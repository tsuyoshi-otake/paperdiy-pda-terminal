#include "wifi_mgr.h"

#include <algorithm>
#include <atomic>
#include <cstring>
#include <mutex>

#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "storage/settings.h"

namespace wifi {
namespace {

constexpr char kTag[] = "wifi";
constexpr EventBits_t kGotIp = BIT0;
constexpr EventBits_t kFailed = BIT1;
constexpr EventBits_t kDisconnected = BIT2;
constexpr int kConnectRetries = 3;
constexpr int kBackoffFirstMs = 5000;
constexpr int kBackoffMaxMs = 60000;

std::function<void()> s_on_change;
std::atomic<State> s_state{State::Off};
EventGroupHandle_t s_events = nullptr;
SemaphoreHandle_t s_op_mtx = nullptr;
esp_timer_handle_t s_retry_timer = nullptr;
std::mutex s_info_mtx;
std::string s_ssid, s_ip, s_error;
std::atomic<int> s_retries{0};
std::atomic<int> s_backoff_ms{kBackoffFirstMs};
std::atomic<bool> s_want_link{false};    // keep the link up: reconnect after drops, with backoff
std::atomic<bool> s_auto_running{false};
std::atomic<bool> s_auto_cancel{false};  // the user took over (connect / disconnect)

void changed()
{
    if (s_on_change) s_on_change();
}

const char* reasonText(uint8_t reason)
{
    switch (reason) {
        case WIFI_REASON_AUTH_FAIL:
        case WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT:
        case WIFI_REASON_HANDSHAKE_TIMEOUT:
        case WIFI_REASON_MIC_FAILURE:
            return "パスワードが違う可能性があります";
        case WIFI_REASON_NO_AP_FOUND:
            return "ネットワークが見つかりません";
        case WIFI_REASON_ASSOC_FAIL:
        case WIFI_REASON_AUTH_EXPIRE:
            return "アクセスポイントに拒否されました";
        case WIFI_REASON_BEACON_TIMEOUT:
            return "電波が弱いか途切れました";
        default:
            return "接続が切れました";
    }
}

void scheduleRetry()
{
    const int ms = s_backoff_ms;
    s_backoff_ms = std::min(ms * 2, kBackoffMaxMs);
    esp_timer_stop(s_retry_timer);
    esp_timer_start_once(s_retry_timer, static_cast<uint64_t>(ms) * 1000);
    ESP_LOGI(kTag, "link lost, retry in %d ms", ms);
}

void onRetryTimer(void*)
{
    if (!s_want_link || s_state == State::Connected || s_state == State::Connecting) return;
    s_retries = 0;
    s_state = State::Connecting;
    changed();
    if (esp_wifi_connect() != ESP_OK) {
        s_state = State::Failed;
        scheduleRetry();
    }
}

// Runs on the system event task: keep it short (no std::string building here).
void onEvent(void*, esp_event_base_t base, int32_t id, void* data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        const uint8_t reason = static_cast<wifi_event_sta_disconnected_t*>(data)->reason;
        xEventGroupSetBits(s_events, kDisconnected);
        const State st = s_state;
        if (st == State::Connecting || st == State::Connected) {
            std::lock_guard<std::mutex> lk(s_info_mtx);
            s_ip.clear();
            char buf[96];
            snprintf(buf, sizeof(buf), "%s (理由 %d)", reasonText(reason), reason);
            s_error = buf;
        }
        if (st == State::Connecting) {
            if (++s_retries <= kConnectRetries) {
                esp_wifi_connect();
            } else {
                s_state = State::Failed;
                xEventGroupSetBits(s_events, kFailed);
                if (s_want_link) scheduleRetry();
            }
        } else if (st == State::Connected) {
            if (s_want_link) {
                s_state = State::Connecting;
                s_retries = 0;
                esp_wifi_connect();
            } else {
                s_state = State::Idle;
            }
        }
        // Idle / Failed: a disconnect we asked for, nothing to do.
        changed();
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        auto* ev = static_cast<ip_event_got_ip_t*>(data);
        {
            std::lock_guard<std::mutex> lk(s_info_mtx);
            char buf[20];
            snprintf(buf, sizeof(buf), IPSTR, IP2STR(&ev->ip_info.ip));
            s_ip = buf;
            s_error.clear();
        }
        s_state = State::Connected;
        s_retries = 0;
        s_backoff_ms = kBackoffFirstMs;
        xEventGroupSetBits(s_events, kGotIp);
        changed();
    }
}

// Drop any current or pending association and wait until the driver confirms it,
// so that late events from the old network cannot be mistaken for the new one.
void dropLink()
{
    s_want_link = false;
    esp_timer_stop(s_retry_timer);
    const State before = s_state;
    s_state = State::Idle;  // the event handler must not reconnect from here on
    xEventGroupClearBits(s_events, kDisconnected);
    if (esp_wifi_disconnect() == ESP_OK && before != State::Idle && before != State::Failed) {
        xEventGroupWaitBits(s_events, kDisconnected, pdTRUE, pdFALSE, pdMS_TO_TICKS(1500));
    }
}

bool connectLocked(const std::string& ssid_in, const std::string& pass, int timeout_ms)
{
    dropLink();

    wifi_config_t cfg = {};
    strncpy(reinterpret_cast<char*>(cfg.sta.ssid), ssid_in.c_str(), sizeof(cfg.sta.ssid) - 1);
    strncpy(reinterpret_cast<char*>(cfg.sta.password), pass.c_str(), sizeof(cfg.sta.password) - 1);
    cfg.sta.threshold.authmode = pass.empty() ? WIFI_AUTH_OPEN : WIFI_AUTH_WPA_PSK;
    cfg.sta.sae_pwe_h2e = WPA3_SAE_PWE_BOTH;
    cfg.sta.pmf_cfg.capable = true;
    esp_err_t err = ESP_FAIL;
    for (int i = 0; i < 3; ++i) {
        err = esp_wifi_set_config(WIFI_IF_STA, &cfg);
        if (err != ESP_ERR_WIFI_STATE) break;
        // still busy with the previous network: disconnect again and give it a moment
        xEventGroupClearBits(s_events, kDisconnected);
        esp_wifi_disconnect();
        xEventGroupWaitBits(s_events, kDisconnected, pdTRUE, pdFALSE, pdMS_TO_TICKS(1000));
    }
    {
        std::lock_guard<std::mutex> lk(s_info_mtx);
        s_ssid = ssid_in;
        s_ip.clear();
        s_error.clear();
        if (err != ESP_OK) s_error = std::string("設定できませんでした (") + esp_err_to_name(err) + ")";
    }
    if (err != ESP_OK) {
        s_state = State::Failed;
        changed();
        return false;
    }

    xEventGroupClearBits(s_events, kGotIp | kFailed);
    s_retries = 0;
    s_state = State::Connecting;
    changed();
    esp_wifi_connect();
    EventBits_t bits =
        xEventGroupWaitBits(s_events, kGotIp | kFailed, pdTRUE, pdFALSE, pdMS_TO_TICKS(timeout_ms));
    bool ok = (bits & kGotIp) != 0;
    if (ok) {
        s_want_link = true;
        s_backoff_ms = kBackoffFirstMs;
        settings::WifiNet net{};
        strncpy(net.ssid, ssid_in.c_str(), sizeof(net.ssid) - 1);
        strncpy(net.pass, pass.c_str(), sizeof(net.pass) - 1);
        settings::wifiSave(net);
    } else {
        if (!(bits & kFailed)) {
            std::lock_guard<std::mutex> lk(s_info_mtx);
            if (s_error.empty()) s_error = "時間内に接続できませんでした";
        }
        s_state = State::Failed;
        esp_wifi_disconnect();
        changed();
    }
    return ok;
}

// Boot-time connection: try the saved networks, and keep trying (with growing pauses)
// until one works or the user connects / disconnects by hand.
void autoConnectTask(void*)
{
    int pause_ms = kBackoffFirstMs * 2;
    while (!s_auto_cancel && s_state != State::Connected) {
        for (const auto& net : settings::wifiList()) {
            if (s_auto_cancel || s_state == State::Connected) break;
            ESP_LOGI(kTag, "auto-connect: %s", net.ssid);
            xSemaphoreTake(s_op_mtx, portMAX_DELAY);
            const bool ok = !s_auto_cancel && connectLocked(net.ssid, net.pass, 12000);
            xSemaphoreGive(s_op_mtx);
            if (ok) break;
        }
        for (int waited = 0; waited < pause_ms && !s_auto_cancel && s_state != State::Connected; waited += 500) {
            vTaskDelay(pdMS_TO_TICKS(500));
        }
        pause_ms = std::min(pause_ms * 2, kBackoffMaxMs);
    }
    s_auto_running = false;
    vTaskDelete(nullptr);
}

}  // namespace

bool start(std::function<void()> on_change)
{
    s_on_change = std::move(on_change);
    s_events = xEventGroupCreate();
    s_op_mtx = xSemaphoreCreateMutex();
    esp_timer_create_args_t targs = {};
    targs.callback = onRetryTimer;
    targs.name = "wifi_retry";
    if (esp_timer_create(&targs, &s_retry_timer) != ESP_OK) return false;
    ESP_ERROR_CHECK(esp_netif_init());
    esp_err_t err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) return false;
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    if (esp_wifi_init(&cfg) != ESP_OK) return false;
    esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, onEvent, nullptr);
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, onEvent, nullptr);
    esp_wifi_set_storage(WIFI_STORAGE_RAM);  // networks are kept in our own NVS list
    esp_wifi_set_mode(WIFI_MODE_STA);
    if (esp_wifi_start() != ESP_OK) return false;
    esp_wifi_set_ps(WIFI_PS_MIN_MODEM);  // required while Bluetooth is active
    s_state = State::Idle;
    changed();
    return true;
}

State state() { return s_state; }

std::string ssid()
{
    std::lock_guard<std::mutex> lk(s_info_mtx);
    return s_ssid;
}

std::string ip()
{
    std::lock_guard<std::mutex> lk(s_info_mtx);
    return s_ip;
}

std::string lastError()
{
    std::lock_guard<std::mutex> lk(s_info_mtx);
    return s_error;
}

std::vector<Ap> scan()
{
    std::vector<Ap> out;
    if (s_state == State::Off) return out;
    xSemaphoreTake(s_op_mtx, portMAX_DELAY);
    wifi_scan_config_t sc = {};
    sc.show_hidden = false;
    if (esp_wifi_scan_start(&sc, true) == ESP_OK) {
        uint16_t n = 0;
        esp_wifi_scan_get_ap_num(&n);
        std::vector<wifi_ap_record_t> recs(std::min<uint16_t>(n, 30));
        uint16_t got = recs.size();
        if (got && esp_wifi_scan_get_ap_records(&got, recs.data()) == ESP_OK) {
            for (uint16_t i = 0; i < got; ++i) {
                std::string name(reinterpret_cast<const char*>(recs[i].ssid));
                if (name.empty()) continue;
                auto it = std::find_if(out.begin(), out.end(), [&](const Ap& a) { return a.ssid == name; });
                if (it == out.end()) {
                    out.push_back({name, recs[i].rssi, recs[i].authmode != WIFI_AUTH_OPEN});
                } else {
                    it->rssi = std::max<int>(it->rssi, recs[i].rssi);
                }
            }
        }
    } else {
        esp_wifi_clear_ap_list();
    }
    xSemaphoreGive(s_op_mtx);
    std::sort(out.begin(), out.end(), [](const Ap& a, const Ap& b) { return a.rssi > b.rssi; });
    return out;
}

bool connect(const std::string& ssid_in, const std::string& pass, int timeout_ms)
{
    if (s_state == State::Off) return false;
    s_auto_cancel = true;  // the user's choice wins over the boot-time auto-connect
    xSemaphoreTake(s_op_mtx, portMAX_DELAY);
    const bool ok = connectLocked(ssid_in, pass, timeout_ms);
    xSemaphoreGive(s_op_mtx);
    return ok;
}

void autoConnectAsync()
{
    if (s_state == State::Off || s_auto_running.exchange(true)) return;
    s_auto_cancel = false;
    if (xTaskCreate(autoConnectTask, "wifi_auto", 4096, nullptr, 3, nullptr) != pdPASS) s_auto_running = false;
}

void disconnect()
{
    s_auto_cancel = true;
    xSemaphoreTake(s_op_mtx, portMAX_DELAY);
    dropLink();
    xSemaphoreGive(s_op_mtx);
    changed();
}

}  // namespace wifi
