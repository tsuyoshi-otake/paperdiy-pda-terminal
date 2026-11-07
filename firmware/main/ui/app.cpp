#include "app.h"

#include <M5Unified.h>

#include <atomic>
#include <cstring>
#include <mutex>

#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "input/ble_kbd.h"
#include "net/ssh_client.h"
#include "net/wifi_mgr.h"
#include "storage/sdcard.h"

using input::KeyEvent;

namespace {

constexpr char kVersion[] = "0.1";
constexpr char kInv[] = "\x1b[7m";
constexpr char kNorm[] = "\x1b[0m";

std::mutex s_closed_mtx;
std::string s_closed_reason;
std::atomic<int> s_battery_pct{-1};
std::atomic<bool> s_charging{false};

void appendUtf8(std::string& s, uint32_t cp)
{
    if (cp < 0x80) {
        s += static_cast<char>(cp);
    } else if (cp < 0x800) {
        s += static_cast<char>(0xC0 | (cp >> 6));
        s += static_cast<char>(0x80 | (cp & 0x3F));
    } else {
        s += static_cast<char>(0xE0 | (cp >> 12));
        s += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        s += static_cast<char>(0x80 | (cp & 0x3F));
    }
}

// All non-display M5Unified calls happen in this task (the library is not thread-safe).
void buttonTask(void*)
{
    int64_t next_battery = 0;
    for (;;) {
        const int64_t now = esp_timer_get_time();
        if (now >= next_battery) {
            s_battery_pct = M5.Power.getBatteryLevel();
            s_charging = M5.Power.isCharging() == m5::Power_Class::is_charging;
            next_battery = now + 10 * 1000 * 1000;
        }
        M5.update();
        if (M5.BtnA.wasClicked()) input::post({input::kKeyButtonA, 0, 0});
        if (M5.BtnB.wasClicked()) input::post({input::kKeyButtonB, 0, 0});
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

bool isCtrlAlt(const KeyEvent& ev, char c)
{
    return ev.key == input::kKeyChar && (ev.mods & (input::kModCtrl | input::kModAlt)) == (input::kModCtrl | input::kModAlt) &&
           (ev.ch == static_cast<uint32_t>(c) || ev.ch == static_cast<uint32_t>(c - 'a' + 'A'));
}

const char* signalText(int rssi)
{
    if (rssi > -55) return "強";
    if (rssi > -70) return "中";
    return "弱";
}

}  // namespace

// ---------------------------------------------------------------------------------------------
// Console helpers
// ---------------------------------------------------------------------------------------------

void App::cls(const char* title)
{
    console_->puts("\x1b[0m\x1b[2J\x1b[H");
    console_->printf("%s %s %s\r\n\r\n", kInv, title, kNorm);
}

void App::say(const std::string& s)
{
    console_->puts(s.c_str());
    console_->puts("\r\n");
}

void App::updateStatus(bool)
{
    battery_pct_ = s_battery_pct;
    charging_ = s_charging;
    std::string left;
    const uint32_t pk = blekbd::passkey();
    if (pk) {
        // Re-pairing can start from auto-reconnect while the user is anywhere in the UI.
        char buf[64];
        snprintf(buf, sizeof(buf), "KB:キーボードで %06lu と Enter", static_cast<unsigned long>(pk));
        left = buf;
    } else switch (blekbd::state()) {
        case blekbd::State::Connected: left = "KB:" + blekbd::deviceName(); break;
        case blekbd::State::Connecting: left = "KB:接続中"; break;
        case blekbd::State::Scanning: left = "KB:検索中"; break;
        default: left = "KB:未接続"; break;
    }
    left += "  Wi-Fi:";
    switch (wifi::state()) {
        case wifi::State::Connected: left += wifi::ssid() + " " + wifi::ip(); break;
        case wifi::State::Connecting: left += "接続中"; break;
        default: left += "未接続"; break;
    }
    if (ssh::state() == ssh::State::Open) left += "  SSH:" + ssh::label();
    char right[32];
    if (battery_pct_ >= 0) snprintf(right, sizeof(right), "%s電池 %d%%", charging_ ? "充電中 " : "", battery_pct_);
    else snprintf(right, sizeof(right), "%s", charging_ ? "充電中" : "");
    renderer_.setStatus(left, right);
}

bool App::getKey(KeyEvent& ev, int timeout_ms)
{
    int waited = 0;
    for (;;) {
        updateStatus();
        const int slice = (timeout_ms < 0) ? 250 : std::min(250, timeout_ms - waited);
        if (xQueueReceive(input::queue(), &ev, pdMS_TO_TICKS(std::max(slice, 1))) == pdTRUE) return true;
        waited += slice;
        if (timeout_ms >= 0 && waited >= timeout_ms) return false;
    }
}

void App::waitAnyKey(const char* msg)
{
    console_->printf("\r\n%s", msg);
    KeyEvent ev;
    getKey(ev, -1);
    console_->puts("\r\n");
}

bool App::readLine(const std::string& prompt, std::string& out, bool mask)
{
    console_->puts(prompt.c_str());
    std::string buf;
    for (;;) {
        KeyEvent ev;
        getKey(ev, -1);
        if (ev.key == input::kKeyEnter) {
            console_->puts("\r\n");
            out = buf;
            return true;
        }
        if (ev.key == input::kKeyEscape) {
            console_->puts("\r\n");
            return false;
        }
        if (ev.key == input::kKeyBackspace) {
            if (buf.empty()) continue;
            size_t n = buf.size() - 1;
            while (n > 0 && (static_cast<uint8_t>(buf[n]) & 0xC0) == 0x80) n--;
            buf.erase(n);
            console_->puts("\b \b");
            continue;
        }
        if (ev.key != input::kKeyChar || (ev.mods & (input::kModCtrl | input::kModAlt))) {
            if (ev.key == input::kKeyChar && (ev.mods & input::kModCtrl) && (ev.ch == 'u' || ev.ch == 'U')) {
                for (size_t i = 0; i < buf.size(); ++i) console_->puts("\b \b");
                buf.clear();
            }
            continue;
        }
        appendUtf8(buf, ev.ch);
        if (mask) {
            console_->puts("*");
        } else {
            std::string echo;
            appendUtf8(echo, ev.ch);
            console_->puts(echo.c_str());
        }
    }
}

int App::readNumber(const std::string& prompt, int max)
{
    for (;;) {
        std::string s;
        if (!readLine(prompt, s) || s.empty()) return -1;
        int n = atoi(s.c_str());
        if (n >= 1 && n <= max) return n;
        say("  1〜" + std::to_string(max) + " の番号を入力してください（Esc で戻る）");
    }
}

bool App::confirm(const std::string& question)
{
    console_->printf("%s [y/N] ", question.c_str());
    for (;;) {
        KeyEvent ev;
        getKey(ev, -1);
        if (ev.key == input::kKeyChar && (ev.ch == 'y' || ev.ch == 'Y')) {
            say("y");
            return true;
        }
        if (ev.key == input::kKeyChar || ev.key == input::kKeyEnter || ev.key == input::kKeyEscape) {
            say("n");
            return false;
        }
    }
}

// ---------------------------------------------------------------------------------------------
// Boot and keyboard pairing
// ---------------------------------------------------------------------------------------------

void App::run()
{
    settings::init();
    prefs_ = settings::prefs();

    auto cfg = M5.config();
    M5.begin(cfg);
    renderer_.begin(&M5.Display, prefs_.font_px, prefs_.rotate180);

    console_ = new term::Vt(renderer_.cols(), renderer_.rows());
    session_ = new term::Vt(renderer_.cols(), renderer_.rows());
    console_->on_change = [this] { renderer_.kick(); };
    session_->on_change = [this] { renderer_.kick(); };
    session_->on_reply = [](const char* d, size_t n) { ssh::write(d, n); };
    renderer_.attach(console_);

    ssh::setHandlers([this](const char* d, size_t n) { session_->feed(d, n); },
                     [](const std::string& reason) {
                         std::lock_guard<std::mutex> lk(s_closed_mtx);
                         s_closed_reason = reason;
                     });

    input::init();
    xTaskCreatePinnedToCore(buttonTask, "buttons", 3072, nullptr, 4, nullptr, 1);

    cls("PaperDIY Terminal");
    console_->printf("バージョン %s\r\n\r\n", kVersion);
    say("Bluetooth と Wi-Fi を準備しています…");
    auto kick_status = [this] { renderer_.kick(); };
    if (!wifi::start(kick_status)) say("Wi-Fi の初期化に失敗しました");
    else if (!settings::wifiList().empty()) wifi::autoConnectAsync();
    if (!blekbd::start(kick_status)) say("Bluetooth の初期化に失敗しました: " + blekbd::lastError());
    sdcard::mount();
    ESP_LOGI("app", "heap after start: internal %u free (largest %u), psram %u free",
             static_cast<unsigned>(heap_caps_get_free_size(MALLOC_CAP_INTERNAL)),
             static_cast<unsigned>(heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL)),
             static_cast<unsigned>(heap_caps_get_free_size(MALLOC_CAP_SPIRAM)));

    bootWaitForKeyboard();
    mainMenu();
}

void App::bootWaitForKeyboard()
{
    settings::Keyboard saved;
    if (settings::keyboardGet(saved)) {
        say(std::string("登録済みのキーボード「") + saved.name + "」を探しています。");
        say("キーボードの電源を入れて、どれかキーを押してください。");
        say("ペアリング待ちの別のキーボードが近くにあれば、そちらに自動でつなぎます。");
        say("一覧から選ぶときはボタンA を押します。");
        for (int i = 0; i < 120; ++i) {  // up to 30 s
            if (blekbd::state() == blekbd::State::Connected) return;
            if (blekbd::passkey()) break;  // pairing another keyboard: the pairing screen shows the passkey
            KeyEvent ev;
            if (getKey(ev, 250) && ev.key == input::kKeyButtonA) break;
        }
        if (blekbd::state() == blekbd::State::Connected) return;
    }
    while (blekbd::state() != blekbd::State::Connected) pairingScreen(false);
}

void App::pairingScreen(bool from_menu)
{
    for (;;) {
        // With no keyboard connected, the Bluetooth task looks for one by itself (blekbd): show how that goes.
        const bool watch_auto = blekbd::state() != blekbd::State::Connected;
        cls("キーボードの接続");
        if (watch_auto) {
            say("キーボードをペアリング（接続待ち）の状態にしてください。近くにあれば自動で見つけて接続します。");
            say("一覧から選ぶときはボタンA を押します。");
        } else {
            say("キーボードをペアリング（接続待ち）の状態にしてから、ボタンA を押すと検索します。");
        }
        settings::Keyboard saved;
        if (settings::keyboardGet(saved)) {
            say(std::string("登録済み: ") + saved.name + "（キーを押せば自動でつながります）");
        }
        if (from_menu) say("ボタンB または Esc で戻ります。");
        say("");

        KeyEvent ev;
        bool start_scan = false;
        bool connecting = false;
        uint32_t shown_pk = 0;
        while (!start_scan) {
            if (watch_auto) {
                const auto st = blekbd::state();
                if (st == blekbd::State::Connected) {
                    say("接続しました: " + blekbd::deviceName());
                    vTaskDelay(pdMS_TO_TICKS(1200));
                    return;
                }
                if (st == blekbd::State::Connecting && !connecting) {
                    connecting = true;
                    const std::string n = blekbd::targetName();
                    say("「" + (n.empty() ? std::string("(名前なし)") : n) + "」に接続しています…");
                }
                const uint32_t pk = blekbd::passkey();
                if (pk && pk != shown_pk) {
                    shown_pk = pk;
                    console_->printf("キーボードで次の数字を入力して Enter を押してください:\r\n\r\n    %s %06lu %s\r\n\r\n",
                                     kInv, static_cast<unsigned long>(pk), kNorm);
                }
                if (connecting && st != blekbd::State::Connecting) {
                    connecting = false;
                    shown_pk = 0;
                    const std::string e = blekbd::lastError();
                    say("つながりませんでした" + (e.empty() ? std::string() : "（" + e + "）") + "。続けて探します。");
                }
            }
            if (!getKey(ev, 500)) continue;
            if (ev.key == input::kKeyButtonA || ev.key == input::kKeyEnter) start_scan = true;
            else if (from_menu && (ev.key == input::kKeyButtonB || ev.key == input::kKeyEscape)) return;
        }

        say("検索しています…（6 秒）");
        bool busy = false;
        auto all = blekbd::scan(6, &busy);
        std::vector<blekbd::Device> devs;
        for (const auto& d : all) {
            if (d.hid) devs.push_back(d);
        }
        if (busy) {
            say("Bluetooth が別の処理で応答しません。しばらく待つか、電源を入れ直してください。");
            waitAnyKey("ボタンA でやり直します");
            continue;
        }
        if (devs.empty()) {
            say("キーボードが見つかりませんでした。");
            if (!all.empty()) {
                say("（HID 以外の Bluetooth 機器は見えています。キーボードが BLE に対応していない可能性があります）");
            }
            waitAnyKey("ボタンA でやり直します");
            continue;
        }
        if (devs.size() > 9) devs.resize(9);

        // The last row leads back to the first screen (re-scan), so the list can be left with buttons only.
        const int rows = static_cast<int>(devs.size()) + 1;
        int sel = 0;
        for (;;) {
            cls("キーボードを選ぶ");
            for (size_t i = 0; i < devs.size(); ++i) {
                console_->printf("%s %zu  %-24s  %d dBm%s\r\n", static_cast<int>(i) == sel ? kInv : "", i + 1,
                                 devs[i].name[0] ? devs[i].name : "(名前なし)", devs[i].rssi, kNorm);
            }
            console_->printf("%s    もう一度検索する / 戻る%s\r\n", sel == rows - 1 ? kInv : "", kNorm);
            say("");
            say("ボタンB: 次へ   ボタンA: 決定   （番号キーでも選べます）");
            getKey(ev, -1);
            if (ev.key == input::kKeyButtonB || ev.key == input::kKeyDown) {
                sel = (sel + 1) % rows;
                continue;
            }
            if (ev.key == input::kKeyUp) {
                sel = (sel + rows - 1) % rows;
                continue;
            }
            if (ev.key == input::kKeyEscape) break;
            if (ev.key == input::kKeyChar && ev.ch >= '1' && ev.ch < '1' + devs.size()) sel = ev.ch - '1';
            else if (ev.key != input::kKeyButtonA && ev.key != input::kKeyEnter) continue;
            if (sel == rows - 1) break;

            const auto& d = devs[sel];
            cls("キーボードの接続");
            console_->printf("「%s」に接続しています…\r\n\r\n", d.name[0] ? d.name : "(名前なし)");
            const uint32_t ticket = blekbd::connectAsync(d);
            uint32_t shown = 0;
            bool done = false, ok = false;
            for (int i = 0; ticket && i < 360 && !done; ++i) {  // up to 90 s (passkey typing takes a while)
                getKey(ev, 250);
                const uint32_t pk = blekbd::passkey();
                if (pk && pk != shown) {
                    shown = pk;
                    console_->printf("キーボードで次の数字を入力して Enter を押してください:\r\n\r\n    %s %06lu %s\r\n\r\n",
                                     kInv, static_cast<unsigned long>(pk), kNorm);
                }
                done = blekbd::connectResult(ticket, ok);
            }
            if (ok) {
                say("接続しました: " + blekbd::deviceName());
                vTaskDelay(pdMS_TO_TICKS(1200));
                return;
            }
            say(std::string("接続できませんでした。") + (done ? blekbd::lastError() : "（時間切れ）"));
            waitAnyKey("ボタンA で戻ります");
            break;
        }
    }
}

// ---------------------------------------------------------------------------------------------
// Menus
// ---------------------------------------------------------------------------------------------

std::string App::menuSummary()
{
    // Only what the menu prints: scanning / connecting states show up in the status bar instead.
    std::string s;
    if (blekbd::state() == blekbd::State::Connected) s += "K" + blekbd::deviceName();
    s += '|';
    if (wifi::state() == wifi::State::Connected) s += "W" + wifi::ssid() + ' ' + wifi::ip();
    s += '|';
    if (ssh::state() == ssh::State::Open) s += "S" + ssh::label();
    s += '|';
    std::lock_guard<std::mutex> lk(s_closed_mtx);
    return s + s_closed_reason;
}

void App::mainMenu()
{
    for (;;) {
        const std::string summary = menuSummary();
        cls("PaperDIY Terminal");
        const bool kb = blekbd::state() == blekbd::State::Connected;
        console_->printf("  キーボード : %s\r\n", kb ? blekbd::deviceName().c_str() : "未接続（ボタンA で接続）");
        if (wifi::state() == wifi::State::Connected) {
            console_->printf("  Wi-Fi      : %s  %s\r\n", wifi::ssid().c_str(), wifi::ip().c_str());
        } else {
            console_->printf("  Wi-Fi      : 未接続\r\n");
        }
        const bool open = ssh::state() == ssh::State::Open;
        console_->printf("  SSH        : %s\r\n", open ? (ssh::label() + "（接続中）").c_str() : "なし");
        {
            std::lock_guard<std::mutex> lk(s_closed_mtx);
            if (!s_closed_reason.empty() && !open) {
                console_->printf("               前回: %s\r\n", s_closed_reason.c_str());
            }
        }
        say("");
        if (open) say("  T  ターミナルに戻る");
        say("  1  SSH で接続する");
        say("  2  SSH の接続先を管理する");
        say("  3  Wi-Fi を設定する");
        say("  4  キーボードを設定する");
        say("  5  表示を設定する");
        say("  6  画面をリフレッシュする");
        if (open) say("  0  SSH を切断する");
        say("");
        say("ターミナル中は ボタンA か Ctrl+Alt+M でこのメニュー、ボタンB で画面リフレッシュ。");

        // Wait for a key; redraw only when the summary above changes (e-paper: no needless refreshes).
        KeyEvent ev;
        bool got = false;
        while (!(got = getKey(ev, 1000)) && menuSummary() == summary) {
        }
        if (!got) continue;
        if (ev.key == input::kKeyButtonA && !kb) {
            pairingScreen(true);
            continue;
        }
        if (ev.key == input::kKeyButtonB) {
            renderer_.requestFullRefresh();
            continue;
        }
        if (ev.key != input::kKeyChar) {
            if (ev.key == input::kKeyEscape && open) terminalLoop();
            continue;
        }
        switch (ev.ch) {
            case 't':
            case 'T':
                if (open) terminalLoop();
                break;
            case '1': sshConnectMenu(); break;
            case '2': sshManageMenu(); break;
            case '3': wifiMenu(); break;
            case '4': keyboardMenu(); break;
            case '5': displayMenu(); break;
            case '6': renderer_.requestFullRefresh(); break;
            case '0':
                if (open) ssh::close();
                break;
            default: break;
        }
    }
}

void App::sshConnectMenu()
{
    auto list = settings::sshList();
    if (list.empty()) {
        cls("SSH で接続");
        say("接続先がまだありません。追加します。");
        say("");
        if (!editProfile(-1)) return;
        list = settings::sshList();
        if (list.empty()) return;
        connectProfile(list.back());
        return;
    }
    cls("SSH で接続");
    for (size_t i = 0; i < list.size(); ++i) {
        console_->printf("  %zu  %-16s %s@%s:%u\r\n", i + 1, list[i].name, list[i].user, list[i].host,
                         list[i].port ? list[i].port : 22);
    }
    say("");
    say("  番号で接続 / a で新しい接続先を追加 / Esc で戻る");
    KeyEvent ev;
    getKey(ev, -1);
    if (ev.key != input::kKeyChar) return;
    if (ev.ch == 'a' || ev.ch == 'A') {
        if (editProfile(-1)) {
            list = settings::sshList();
            if (!list.empty()) connectProfile(list.back());
        }
        return;
    }
    const int n = static_cast<int>(ev.ch) - '0';
    if (n >= 1 && n <= static_cast<int>(list.size())) connectProfile(list[n - 1]);
}

void App::sshManageMenu()
{
    for (;;) {
        auto list = settings::sshList();
        cls("SSH の接続先");
        if (list.empty()) say("  （まだありません）");
        for (size_t i = 0; i < list.size(); ++i) {
            console_->printf("  %zu  %-16s %s@%s:%u%s%s\r\n", i + 1, list[i].name, list[i].user, list[i].host,
                             list[i].port ? list[i].port : 22, list[i].pass[0] ? "  [パスワード保存]" : "",
                             list[i].keyfile[0] ? "  [鍵]" : "");
        }
        say("");
        say("  a 追加   e 編集   d 削除   Esc 戻る");
        KeyEvent ev;
        getKey(ev, -1);
        if (ev.key == input::kKeyEscape || ev.key == input::kKeyButtonB) return;
        if (ev.key != input::kKeyChar) continue;
        if (ev.ch == 'a' || ev.ch == 'A') {
            editProfile(-1);
        } else if ((ev.ch == 'e' || ev.ch == 'E') && !list.empty()) {
            int n = readNumber("編集する番号: ", list.size());
            if (n > 0) editProfile(n - 1);
        } else if ((ev.ch == 'd' || ev.ch == 'D') && !list.empty()) {
            int n = readNumber("削除する番号: ", list.size());
            if (n > 0 && confirm(std::string("「") + list[n - 1].name + "」を削除しますか？")) settings::sshRemove(n - 1);
        }
    }
}

bool App::editProfile(int index)
{
    auto list = settings::sshList();
    settings::SshProfile p{};
    p.port = 22;
    const bool is_new = index < 0 || index >= static_cast<int>(list.size());
    if (!is_new) p = list[index];
    if (is_new && list.size() >= settings::kMaxSsh) {
        say("接続先は " + std::to_string(settings::kMaxSsh) + " 件までです。");
        waitAnyKey();
        return false;
    }
    cls(is_new ? "接続先を追加" : "接続先を編集");
    say("空欄のまま Enter で現在の値を残します。Esc で中止。");
    say("");

    auto field = [&](const char* label, char* dst, size_t cap, bool mask, bool clearable) -> bool {
        std::string cur = dst;
        std::string shown = mask ? (cur.empty() ? "" : "****") : cur;
        std::string prompt = std::string(label) + (shown.empty() ? "" : " [" + shown + "]") + ": ";
        std::string v;
        if (!readLine(prompt, v, mask)) return false;
        if (clearable && v == "-") v.clear(), cur.clear(), dst[0] = 0;
        else if (!v.empty()) {
            strncpy(dst, v.c_str(), cap - 1);
            dst[cap - 1] = 0;
        }
        return true;
    };

    if (!field("名前", p.name, sizeof(p.name), false, false)) return false;
    if (!field("ホスト（名前または IP）", p.host, sizeof(p.host), false, false)) return false;
    char port[8];
    snprintf(port, sizeof(port), "%u", p.port ? p.port : 22);
    if (!field("ポート", port, sizeof(port), false, false)) return false;
    p.port = static_cast<uint16_t>(atoi(port) > 0 && atoi(port) < 65536 ? atoi(port) : 22);
    if (!field("ユーザー名", p.user, sizeof(p.user), false, false)) return false;
    say("パスワードを保存しない場合は空欄にすると、接続のたびに聞きます（- で保存済みを消去）。");
    if (!field("パスワード", p.pass, sizeof(p.pass), true, true)) return false;
    say("公開鍵認証を使う場合は microSD 上の秘密鍵のパス（例 /sd/id_ecdsa、PEM 形式）。- で消去。");
    if (!field("鍵ファイル", p.keyfile, sizeof(p.keyfile), false, true)) return false;

    if (!p.host[0] || !p.user[0]) {
        say("ホストとユーザー名は必須です。保存しませんでした。");
        waitAnyKey();
        return false;
    }
    if (!p.name[0]) strncpy(p.name, p.host, sizeof(p.name) - 1);
    settings::sshSave(is_new ? -1 : index, p);
    say("保存しました。");
    vTaskDelay(pdMS_TO_TICKS(600));
    return true;
}

void App::connectProfile(const settings::SshProfile& p)
{
    cls("SSH で接続");
    if (wifi::state() != wifi::State::Connected) {
        say("Wi-Fi に接続していません。先に Wi-Fi を設定してください。");
        waitAnyKey();
        return;
    }
    ssh::Prompter ui;
    ui.status = [this](const std::string& m) { say(m); };
    ui.confirm = [this](const std::string& q) { return confirm(q); };
    ui.ask = [this](const std::string& prompt, bool echo, std::string& ans) { return readLine(prompt, ans, !echo); };
    {
        std::lock_guard<std::mutex> lk(s_closed_mtx);
        s_closed_reason.clear();
    }
    session_->reset();
    std::string err;
    if (!ssh::connect(p, renderer_.cols(), renderer_.rows(), ui, err)) {
        say("");
        say("接続できませんでした: " + err);
        waitAnyKey();
        return;
    }
    terminalLoop();
}

void App::terminalLoop()
{
    renderer_.attach(session_);
    for (;;) {
        KeyEvent ev;
        const bool got = getKey(ev, 250);
        if (ssh::state() != ssh::State::Open) break;
        if (!got) continue;
        if (ev.key == input::kKeyButtonA || isCtrlAlt(ev, 'm')) break;
        if (ev.key == input::kKeyButtonB || isCtrlAlt(ev, 'r')) {
            renderer_.requestFullRefresh();
            continue;
        }
        const std::string seq = encodeKey(ev, session_->appCursorKeys());
        if (!seq.empty()) ssh::write(seq.data(), seq.size());
    }
    renderer_.attach(console_);
}

void App::wifiMenu()
{
    for (;;) {
        cls("Wi-Fi の設定");
        if (wifi::state() == wifi::State::Connected) {
            console_->printf("  接続中: %s  %s\r\n", wifi::ssid().c_str(), wifi::ip().c_str());
        } else {
            console_->printf("  未接続 %s\r\n", wifi::lastError().c_str());
        }
        say("");
        say("  1  ネットワークを検索して接続");
        say("  2  SSID を入力して接続（非公開のネットワーク）");
        say("  3  保存済みのネットワーク");
        say("  Esc  戻る");
        KeyEvent ev;
        getKey(ev, -1);
        if (ev.key == input::kKeyEscape || ev.key == input::kKeyButtonB) return;
        if (ev.key != input::kKeyChar) continue;

        if (ev.ch == '1') {
            cls("Wi-Fi を検索");
            say("検索しています…");
            auto aps = wifi::scan();
            if (aps.size() > 15) aps.resize(15);
            cls("Wi-Fi を検索");
            if (aps.empty()) {
                say("見つかりませんでした。");
                waitAnyKey();
                continue;
            }
            for (size_t i = 0; i < aps.size(); ++i) {
                console_->printf("  %2zu  %-32s  %s  %s\r\n", i + 1, aps[i].ssid.c_str(), signalText(aps[i].rssi),
                                 aps[i].secure ? "保護" : "公開");
            }
            say("");
            int n = readNumber("番号（Esc で戻る）: ", aps.size());
            if (n < 0) continue;
            std::string pass;
            if (aps[n - 1].secure && !readLine("パスワード: ", pass, true)) continue;
            wifiConnect(aps[n - 1].ssid, pass);
        } else if (ev.ch == '2') {
            std::string ssid, pass;
            if (!readLine("SSID: ", ssid) || ssid.empty()) continue;
            if (!readLine("パスワード（なしなら空欄）: ", pass, true)) continue;
            wifiConnect(ssid, pass);
        } else if (ev.ch == '3') {
            auto saved = settings::wifiList();
            cls("保存済みのネットワーク");
            if (saved.empty()) {
                say("まだありません。");
                waitAnyKey();
                continue;
            }
            for (size_t i = 0; i < saved.size(); ++i) console_->printf("  %zu  %s\r\n", i + 1, saved[i].ssid);
            say("");
            std::string cmd;
            if (!readLine("番号で接続、d と番号で削除（例 d2）: ", cmd) || cmd.empty()) continue;
            const bool del = (cmd[0] == 'd' || cmd[0] == 'D');
            const int n = atoi(cmd.c_str() + (del ? 1 : 0));
            if (n < 1 || n > static_cast<int>(saved.size())) continue;
            if (del) {
                settings::wifiRemove(saved[n - 1].ssid);
            } else {
                wifiConnect(saved[n - 1].ssid, saved[n - 1].pass);
            }
        }
    }
}

void App::wifiConnect(const std::string& ssid, const std::string& pass)
{
    console_->printf("「%s」に接続しています…\r\n", ssid.c_str());
    if (wifi::connect(ssid, pass)) {
        say("接続しました: " + wifi::ip() + "（次回から自動で接続します）");
    } else {
        say("接続できませんでした: " + wifi::lastError());
    }
    waitAnyKey();
}

void App::keyboardMenu()
{
    for (;;) {
        cls("キーボード");
        if (blekbd::state() == blekbd::State::Connected) {
            const int lv = blekbd::batteryLevel();
            if (lv >= 0) console_->printf("  接続中: %s（電池 %d%%）\r\n", blekbd::deviceName().c_str(), lv);
            else console_->printf("  接続中: %s\r\n", blekbd::deviceName().c_str());
        } else {
            say("  未接続");
        }
        say("");
        say("  1  別のキーボードをペアリングする");
        say("  2  登録を解除する");
        say("  Esc  戻る");
        KeyEvent ev;
        getKey(ev, -1);
        if (ev.key == input::kKeyEscape || ev.key == input::kKeyButtonB) return;
        if (ev.key != input::kKeyChar) continue;
        if (ev.ch == '1') {
            pairingScreen(true);
        } else if (ev.ch == '2') {
            if (confirm("登録を解除しますか？（再起動後にペアリングし直します）")) {
                blekbd::forget();
                say("解除しました。キーボード側に残っているペアリング情報も消しておくと確実です。");
                waitAnyKey();
                if (blekbd::state() != blekbd::State::Connected) pairingScreen(false);
            }
        }
    }
}

void App::applyFont(int px)
{
    renderer_.setFont(px);
    console_->resize(renderer_.cols(), renderer_.rows());
    session_->resize(renderer_.cols(), renderer_.rows());
    if (ssh::state() == ssh::State::Open) ssh::resize(renderer_.cols(), renderer_.rows());
    prefs_.font_px = static_cast<uint8_t>(px);
    settings::prefsSet(prefs_);
}

void App::displayMenu()
{
    for (;;) {
        cls("表示");
        console_->printf("  1  文字サイズ: %dpx（%d 桁 x %d 行）\r\n", renderer_.fontPx(), renderer_.cols(), renderer_.rows());
        console_->printf("  2  画面の上下反転: %s\r\n", prefs_.rotate180 ? "オン" : "オフ");
        say("  Esc  戻る");
        KeyEvent ev;
        getKey(ev, -1);
        if (ev.key == input::kKeyEscape || ev.key == input::kKeyButtonB) return;
        if (ev.key != input::kKeyChar) continue;
        if (ev.ch == '1') {
            applyFont(renderer_.fontPx() == 24 ? 16 : 24);
        } else if (ev.ch == '2') {
            prefs_.rotate180 = !prefs_.rotate180;
            renderer_.setRotate180(prefs_.rotate180);
            settings::prefsSet(prefs_);
        }
    }
}

// ---------------------------------------------------------------------------------------------
// Key encoding for the remote terminal (xterm conventions)
// ---------------------------------------------------------------------------------------------

std::string App::encodeKey(const KeyEvent& ev, bool app_cursor) const
{
    using namespace input;
    const bool ctrl = ev.mods & kModCtrl, alt = ev.mods & kModAlt, shift = ev.mods & kModShift;
    // xterm modifier parameter: 1 + shift(1) + alt(2) + ctrl(4)
    const int modp = 1 + (shift ? 1 : 0) + (alt ? 2 : 0) + (ctrl ? 4 : 0);
    auto csi = [&](char final_char) -> std::string {
        if (modp > 1) return std::string("\x1b[1;") + std::to_string(modp) + final_char;
        return std::string(app_cursor ? "\x1bO" : "\x1b[") + final_char;
    };
    auto tilde = [&](int n) -> std::string {
        if (modp > 1) return "\x1b[" + std::to_string(n) + ";" + std::to_string(modp) + "~";
        return "\x1b[" + std::to_string(n) + "~";
    };
    switch (ev.key) {
        case kKeyChar: {
            uint32_t c = ev.ch;
            if (ctrl) {
                if (c >= 'a' && c <= 'z') c = c - 'a' + 1;
                else if (c >= 'A' && c <= 'Z') c = c - 'A' + 1;
                else if (c == ' ' || c == '@' || c == '2') c = 0;
                else if (c == '[' || c == '3') c = 0x1b;
                else if (c == '\\' || c == '4') c = 0x1c;
                else if (c == ']' || c == '5') c = 0x1d;
                else if (c == '^' || c == '6') c = 0x1e;
                else if (c == '_' || c == '-' || c == '7' || c == '/') c = 0x1f;
                else if (c == '8' || c == '?') c = 0x7f;
            }
            std::string s = alt ? "\x1b" : "";
            if (c == 0) s.push_back('\0');
            else appendUtf8(s, c);
            return s;
        }
        case kKeyEnter: return alt ? "\x1b\r" : "\r";
        case kKeyEscape: return "\x1b";
        case kKeyBackspace: return ctrl ? "\x08" : (alt ? "\x1b\x7f" : "\x7f");
        case kKeyTab: return shift ? "\x1b[Z" : "\t";
        case kKeyUp: return csi('A');
        case kKeyDown: return csi('B');
        case kKeyRight: return csi('C');
        case kKeyLeft: return csi('D');
        case kKeyHome: return csi('H');
        case kKeyEnd: return csi('F');
        case kKeyInsert: return tilde(2);
        case kKeyDelete: return tilde(3);
        case kKeyPageUp: return tilde(5);
        case kKeyPageDown: return tilde(6);
        default: break;
    }
    if (ev.key >= kKeyF1 && ev.key <= kKeyF12) {
        const int f = ev.key - kKeyF1 + 1;
        if (f <= 4) {
            const char fin = static_cast<char>('P' + f - 1);
            if (modp > 1) return std::string("\x1b[1;") + std::to_string(modp) + fin;
            return std::string("\x1bO") + fin;
        }
        static const int codes[] = {15, 17, 18, 19, 20, 21, 23, 24};
        return tilde(codes[f - 5]);
    }
    return "";
}
