#include "ssh_client.h"

#include <fcntl.h>
#include <libssh2.h>
#include <sys/stat.h>

#include <atomic>
#include <cerrno>
#include <cstring>
#include <mutex>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/stream_buffer.h"
#include "freertos/task.h"
#include "lwip/netdb.h"
#include "lwip/sockets.h"
#include "mbedtls/base64.h"
#include "storage/sdcard.h"

namespace ssh {
namespace {

constexpr char kTag[] = "ssh";

std::function<void(const char*, size_t)> s_on_data;
std::function<void(const std::string&)> s_on_closed;
std::atomic<State> s_state{State::Idle};
std::atomic<bool> s_stop{false};
std::atomic<int> s_new_cols{0}, s_new_rows{0};

LIBSSH2_SESSION* s_session = nullptr;
LIBSSH2_CHANNEL* s_channel = nullptr;
int s_sock = -1;
StreamBufferHandle_t s_tx = nullptr;
SemaphoreHandle_t s_tx_mtx = nullptr;
std::atomic<bool> s_task_running{false};
std::mutex s_label_mtx;
std::string s_label;

struct KbdCtx {
    Prompter* ui;
    std::string password;
    int round;
};
KbdCtx* s_kbd = nullptr;

std::string sessionError()
{
    if (!s_session) return "不明なエラー";
    char* msg = nullptr;
    int len = 0;
    libssh2_session_last_error(s_session, &msg, &len, 0);
    return msg ? std::string(msg, len) : "不明なエラー";
}

int openSocket(const char* host, uint16_t port, std::string& err)
{
    addrinfo hints = {};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    addrinfo* res = nullptr;
    char port_str[8];
    snprintf(port_str, sizeof(port_str), "%u", port);
    if (getaddrinfo(host, port_str, &hints, &res) != 0 || !res) {
        err = std::string("ホスト名を解決できません: ") + host;
        return -1;
    }
    int sock = -1;
    int last_errno = 0;
    for (addrinfo* ai = res; ai; ai = ai->ai_next) {
        sock = socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol);
        if (sock < 0) continue;
        const int flags = fcntl(sock, F_GETFL, 0);
        fcntl(sock, F_SETFL, flags | O_NONBLOCK);
        int rc = ::connect(sock, ai->ai_addr, ai->ai_addrlen);
        if (rc != 0 && errno == EINPROGRESS) {
            fd_set wfds;
            FD_ZERO(&wfds);
            FD_SET(sock, &wfds);
            timeval tv = {10, 0};
            rc = select(sock + 1, nullptr, &wfds, nullptr, &tv);
            if (rc > 0) {
                int so_err = 0;
                socklen_t l = sizeof(so_err);
                getsockopt(sock, SOL_SOCKET, SO_ERROR, &so_err, &l);
                rc = so_err ? -1 : 0;
                if (so_err) errno = so_err;
            } else {
                if (rc == 0) errno = ETIMEDOUT;
                rc = -1;
            }
        }
        if (rc == 0) {
            fcntl(sock, F_SETFL, flags);
            break;
        }
        last_errno = errno;
        ::close(sock);
        sock = -1;
    }
    freeaddrinfo(res);
    if (sock < 0) {
        err = std::string("サーバーに接続できません (") + strerror(last_errno) + ")";
        return -1;
    }
    int one = 1;
    setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
    setsockopt(sock, SOL_SOCKET, SO_KEEPALIVE, &one, sizeof(one));
    // lwIP's default keepalive idle time is 2 hours; notice a dead link in about 2 minutes instead.
    int idle = 60, intvl = 15, cnt = 4;
    setsockopt(sock, IPPROTO_TCP, TCP_KEEPIDLE, &idle, sizeof(idle));
    setsockopt(sock, IPPROTO_TCP, TCP_KEEPINTVL, &intvl, sizeof(intvl));
    setsockopt(sock, IPPROTO_TCP, TCP_KEEPCNT, &cnt, sizeof(cnt));
    return sock;
}

std::string hostKeyFingerprint(std::string& type)
{
    size_t len = 0;
    int t = 0;
    libssh2_session_hostkey(s_session, &len, &t);
    switch (t) {
        case LIBSSH2_HOSTKEY_TYPE_RSA: type = "RSA"; break;
        case LIBSSH2_HOSTKEY_TYPE_ECDSA_256: type = "ECDSA-256"; break;
        case LIBSSH2_HOSTKEY_TYPE_ECDSA_384: type = "ECDSA-384"; break;
        case LIBSSH2_HOSTKEY_TYPE_ECDSA_521: type = "ECDSA-521"; break;
        case LIBSSH2_HOSTKEY_TYPE_ED25519: type = "ED25519"; break;
        default: type = "?"; break;
    }
    const char* hash = libssh2_hostkey_hash(s_session, LIBSSH2_HOSTKEY_HASH_SHA256);
    if (!hash) return "";
    unsigned char b64[64];
    size_t olen = 0;
    mbedtls_base64_encode(b64, sizeof(b64), &olen, reinterpret_cast<const unsigned char*>(hash), 32);
    std::string s(reinterpret_cast<char*>(b64), olen);
    while (!s.empty() && s.back() == '=') s.pop_back();  // OpenSSH style
    return "SHA256:" + s;
}

LIBSSH2_USERAUTH_KBDINT_RESPONSE_FUNC(kbdCallback)
{
    (void)name;
    (void)name_len;
    (void)instruction;
    (void)instruction_len;
    (void)abstract;
    KbdCtx* ctx = s_kbd;
    for (int i = 0; i < num_prompts; ++i) {
        std::string prompt(reinterpret_cast<const char*>(prompts[i].text), prompts[i].length);
        std::string answer;
        if (!prompts[i].echo && ctx && ctx->round == 0 && !ctx->password.empty()) {
            answer = ctx->password;
        } else if (ctx) {
            ctx->ui->ask(prompt, prompts[i].echo != 0, answer);
        }
        responses[i].text = static_cast<char*>(malloc(answer.size() + 1));
        if (responses[i].text) {
            memcpy(responses[i].text, answer.c_str(), answer.size() + 1);
            responses[i].length = answer.size();
        }
    }
    if (ctx) ctx->round++;
}

// graceful: the link is believed healthy, so say goodbye to the server first.
// Otherwise (or when the goodbye fails) shut the socket down so that libssh2 sees a
// disconnect and frees everything at once instead of timing out and leaking.
void cleanup(bool graceful)
{
    bool link_ok = graceful && s_sock >= 0;
    if (s_session) {
        libssh2_session_set_blocking(s_session, 1);
        libssh2_session_set_timeout(s_session, 1500);
    }
    if (s_channel) {
        if (link_ok && libssh2_channel_close(s_channel) != 0) link_ok = false;
        if (!link_ok && s_sock >= 0) shutdown(s_sock, SHUT_RDWR);
        if (libssh2_channel_free(s_channel) != 0) ESP_LOGW(kTag, "channel_free failed");
        s_channel = nullptr;
    }
    if (s_session) {
        if (link_ok && libssh2_session_disconnect(s_session, "bye") != 0) link_ok = false;
        if (!link_ok && s_sock >= 0) shutdown(s_sock, SHUT_RDWR);
        if (libssh2_session_free(s_session) != 0) ESP_LOGW(kTag, "session_free failed");
        s_session = nullptr;
    }
    if (s_sock >= 0) {
        ::close(s_sock);
        s_sock = -1;
    }
}

void ioTask(void*)
{
    static char buf[2048];
    std::string pending;
    std::string reason = "サーバーが接続を閉じました";
    bool failed = false;
    while (!s_stop) {
        fd_set rfds, wfds;
        FD_ZERO(&rfds);
        FD_ZERO(&wfds);
        FD_SET(s_sock, &rfds);
        const int dir = libssh2_session_block_directions(s_session);
        if (dir & LIBSSH2_SESSION_BLOCK_OUTBOUND) FD_SET(s_sock, &wfds);
        timeval tv = {0, 15000};
        select(s_sock + 1, &rfds, &wfds, nullptr, &tv);

        for (int stream : {0, SSH_EXTENDED_DATA_STDERR}) {
            for (;;) {
                ssize_t n = libssh2_channel_read_ex(s_channel, stream, buf, sizeof(buf));
                if (n > 0) {
                    if (s_on_data) s_on_data(buf, static_cast<size_t>(n));
                    continue;
                }
                if (n < 0 && n != LIBSSH2_ERROR_EAGAIN) {
                    reason = "通信エラー: " + sessionError();
                    failed = true;
                }
                break;
            }
            if (failed) break;
        }
        if (failed || libssh2_channel_eof(s_channel)) break;

        if (pending.empty()) {
            size_t got = xStreamBufferReceive(s_tx, buf, sizeof(buf), 0);
            if (got) pending.assign(buf, got);
        }
        while (!pending.empty()) {
            ssize_t w = libssh2_channel_write(s_channel, pending.data(), pending.size());
            if (w == LIBSSH2_ERROR_EAGAIN) break;
            if (w < 0) {
                reason = "送信エラー: " + sessionError();
                failed = true;
                break;
            }
            pending.erase(0, static_cast<size_t>(w));
        }
        if (failed) break;

        const int c = s_new_cols.exchange(0);
        if (c) {
            if (libssh2_channel_request_pty_size(s_channel, c, s_new_rows.load()) == LIBSSH2_ERROR_EAGAIN) {
                s_new_cols = c;  // retry next round
            }
        }
        int next = 0;
        libssh2_keepalive_send(s_session, &next);
    }
    const bool user_closed = s_stop;
    cleanup(!failed);
    s_state = State::Idle;
    ESP_LOGI(kTag, "session ended: %s", user_closed ? "by user" : reason.c_str());
    if (s_on_closed) s_on_closed(user_closed ? "切断しました" : reason);
    s_task_running = false;
    vTaskDelete(nullptr);
}

bool fail(std::string& error, const std::string& msg)
{
    error = msg;
    cleanup(true);
    s_state = State::Idle;
    return false;
}

}  // namespace

void setHandlers(std::function<void(const char*, size_t)> on_data, std::function<void(const std::string&)> on_closed)
{
    s_on_data = std::move(on_data);
    s_on_closed = std::move(on_closed);
}

bool connect(const settings::SshProfile& p, int cols, int rows, Prompter& ui, std::string& error)
{
    close();  // also waits for a session that ended by itself to finish cleaning up
    if (!s_tx) {
        s_tx = xStreamBufferCreate(4096, 1);
        s_tx_mtx = xSemaphoreCreateMutex();
        libssh2_init(0);
    }
    xStreamBufferReset(s_tx);
    s_state = State::Connecting;
    const uint16_t port = p.port ? p.port : 22;
    char where[120];
    snprintf(where, sizeof(where), "%s@%s:%u", p.user, p.host, port);

    ui.status(std::string("接続しています: ") + where);
    std::string err;
    s_sock = openSocket(p.host, port, err);
    if (s_sock < 0) return fail(error, err);

    s_session = libssh2_session_init();
    if (!s_session) return fail(error, "メモリ不足（セッションを作れません）");
    libssh2_session_set_blocking(s_session, 1);
    libssh2_session_set_timeout(s_session, 20000);
    ui.status("暗号化の準備をしています…");
    if (libssh2_session_handshake(s_session, s_sock) != 0) return fail(error, "SSH の開始に失敗: " + sessionError());

    // Host key: trust on first use, warn loudly when it changes.
    std::string type;
    const std::string fp = hostKeyFingerprint(type);
    char hp[80];
    snprintf(hp, sizeof(hp), "%s:%u", p.host, port);
    std::string known;
    if (!settings::knownHostGet(hp, known)) {
        if (!ui.confirm("初めて接続するサーバーです。\r\n  " + type + " " + fp +
                        "\r\nサーバー側の鍵と一致することを確認してください。この鍵を保存して続けますか？")) {
            return fail(error, "ホスト鍵を承認しませんでした");
        }
        settings::knownHostSet(hp, fp);
    } else if (known != fp) {
        ui.status("\x1b[7m 警告: サーバーの鍵が前回と違います \x1b[0m\r\n  前回: " + known + "\r\n  今回: " + fp +
                  "\r\n  サーバーの入れ替えでなければ、なりすましの可能性があります。");
        std::string ans;
        if (!ui.ask("それでも接続するなら yes と入力: ", true, ans) || ans != "yes") {
            return fail(error, "接続を中止しました");
        }
        settings::knownHostSet(hp, fp);
    }

    ui.status("認証しています…");
    const char* list = libssh2_userauth_list(s_session, p.user, strlen(p.user));
    bool authed = libssh2_userauth_authenticated(s_session) != 0;
    if (!list && !authed) return fail(error, "認証方式を取得できません: " + sessionError());
    const std::string methods = list ? list : "";

    if (!authed && p.keyfile[0] && methods.find("publickey") != std::string::npos) {
        if (strncmp(p.keyfile, "/sd/", 4) == 0) sdcard::mount();
        struct stat st;
        if (stat(p.keyfile, &st) != 0) {
            ui.status(std::string("鍵ファイルが見つかりません: ") + p.keyfile);
        } else {
            int rc = libssh2_userauth_publickey_fromfile(s_session, p.user, nullptr, p.keyfile, "");
            if (rc == LIBSSH2_ERROR_FILE) {  // probably protected by a passphrase
                std::string phrase;
                if (ui.ask("鍵のパスフレーズ: ", false, phrase)) {
                    rc = libssh2_userauth_publickey_fromfile(s_session, p.user, nullptr, p.keyfile, phrase.c_str());
                }
            }
            if (rc == 0) authed = true;
            else ui.status("公開鍵認証に失敗: " + sessionError());
        }
    }
    if (!authed && methods.find("password") != std::string::npos) {
        std::string pw = p.pass;
        for (int attempt = 0; attempt < 3 && !authed; ++attempt) {
            if (pw.empty() && !ui.ask(std::string(p.user) + "@" + p.host + " のパスワード: ", false, pw)) break;
            if (libssh2_userauth_password(s_session, p.user, pw.c_str()) == 0) {
                authed = true;
            } else {
                ui.status("パスワードが違います");
                pw.clear();
            }
        }
    }
    if (!authed && methods.find("keyboard-interactive") != std::string::npos) {
        KbdCtx ctx{&ui, p.pass, 0};
        s_kbd = &ctx;
        authed = libssh2_userauth_keyboard_interactive(s_session, p.user, kbdCallback) == 0;
        s_kbd = nullptr;
    }
    if (!authed) return fail(error, "認証に失敗しました（サーバーの方式: " + methods + "）");

    ui.status("シェルを開いています…");
    s_channel = libssh2_channel_open_session(s_session);
    if (!s_channel) return fail(error, "チャンネルを開けません: " + sessionError());
    if (libssh2_channel_request_pty_ex(s_channel, "xterm", 5, nullptr, 0, cols, rows, 0, 0) != 0) {
        return fail(error, "端末を確保できません: " + sessionError());
    }
    if (libssh2_channel_shell(s_channel) != 0) return fail(error, "シェルを起動できません: " + sessionError());
    // want_reply=0: OpenSSH answers keepalives with REQUEST_FAILURE, which libssh2 would queue and never free.
    libssh2_keepalive_config(s_session, 0, 30);
    libssh2_session_set_blocking(s_session, 0);

    {
        std::lock_guard<std::mutex> lk(s_label_mtx);
        s_label = std::string(p.user) + "@" + p.host;
    }
    s_stop = false;
    s_new_cols = 0;
    s_state = State::Open;
    s_task_running = true;
    if (xTaskCreatePinnedToCore(ioTask, "ssh_io", 12288, nullptr, 6, nullptr, 0) != pdPASS) {
        s_task_running = false;
        return fail(error, "メモリ不足（通信タスクを作れません）");
    }
    return true;
}

void write(const char* data, size_t len)
{
    if (s_state != State::Open || !s_tx || len == 0) return;
    xSemaphoreTake(s_tx_mtx, portMAX_DELAY);
    xStreamBufferSend(s_tx, data, len, pdMS_TO_TICKS(50));
    xSemaphoreGive(s_tx_mtx);
}

void resize(int cols, int rows)
{
    s_new_rows = rows;
    s_new_cols = cols;
}

void close()
{
    if (!s_task_running) return;
    s_stop = true;
    // No timeout: the io task owns s_session / s_sock until it has cleaned up (a few seconds at most).
    while (s_task_running) vTaskDelay(pdMS_TO_TICKS(10));
}

State state() { return s_state; }

std::string label()
{
    std::lock_guard<std::mutex> lk(s_label_mtx);
    return s_label;
}

}  // namespace ssh
