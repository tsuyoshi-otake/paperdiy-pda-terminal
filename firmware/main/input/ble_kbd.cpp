#include "ble_kbd.h"

#include <algorithm>
#include <atomic>
#include <cstring>
#include <mutex>

#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gattc_api.h"
#include "esp_hidh.h"
#include "esp_hidh_gattc.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "keyboard.h"
#include "storage/settings.h"

namespace blekbd {
namespace {

constexpr char kTag[] = "blekbd";
constexpr uint16_t kHidServiceUuid = 0x1812;

std::function<void()> s_on_change;
std::atomic<State> s_state{State::Off};
std::atomic<uint32_t> s_passkey{0};
std::atomic<int> s_battery{-1};
std::atomic<bool> s_auto{true};
std::mutex s_info_mtx;
std::string s_name;
std::string s_error;

SemaphoreHandle_t s_op_mtx = nullptr;    // serialises scan / connect
SemaphoreHandle_t s_scan_param = nullptr;
SemaphoreHandle_t s_scan_done = nullptr;
std::mutex s_found_mtx;
std::vector<Device> s_found;

struct Request {
    Device dev;
    uint32_t ticket;
};
QueueHandle_t s_requests = nullptr;      // Request to connect, from the UI
std::atomic<uint32_t> s_next_ticket{1};
std::atomic<uint32_t> s_done_ticket{0};  // last finished UI request
std::atomic<bool> s_done_ok{false};

// The connected keyboard and the one being opened. esp_hidh may close (and free) a device
// while esp_hidh_dev_open() is still blocked, so we track devices by address, not pointer.
std::mutex s_dev_mtx;
esp_hidh_dev_t* s_dev = nullptr;
uint8_t s_dev_bda[6] = {};
uint8_t s_target_bda[6] = {};
bool s_target_active = false;
bool s_target_lost = false;
std::atomic<bool> s_auth_failed{false};

bool currentAlive()
{
    std::lock_guard<std::mutex> lk(s_dev_mtx);
    return s_dev && esp_hidh_dev_exists(s_dev);
}

void changed()
{
    if (s_on_change) s_on_change();
}

void setError(const std::string& e)
{
    std::lock_guard<std::mutex> lk(s_info_mtx);
    s_error = e;
}

void handleAdv(const esp_ble_gap_cb_param_t::ble_scan_result_evt_param& r)
{
    uint8_t* adv = const_cast<uint8_t*>(r.ble_adv);
    const uint16_t total = r.adv_data_len + r.scan_rsp_len;
    Device d{};
    memcpy(d.bda, r.bda, 6);
    d.addr_type = r.ble_addr_type;
    d.rssi = r.rssi;

    uint8_t len = 0;
    uint8_t* p = esp_ble_resolve_adv_data_by_type(adv, total, ESP_BLE_AD_TYPE_NAME_CMPL, &len);
    if (!p) p = esp_ble_resolve_adv_data_by_type(adv, total, ESP_BLE_AD_TYPE_NAME_SHORT, &len);
    if (p && len) memcpy(d.name, p, std::min<size_t>(len, sizeof(d.name) - 1));

    p = esp_ble_resolve_adv_data_by_type(adv, total, ESP_BLE_AD_TYPE_APPEARANCE, &len);
    if (p && len >= 2) d.appearance = p[0] | (p[1] << 8);

    bool hid = (d.appearance >= 0x03C0 && d.appearance <= 0x03CF);
    for (auto type : {ESP_BLE_AD_TYPE_16SRV_CMPL, ESP_BLE_AD_TYPE_16SRV_PART}) {
        p = esp_ble_resolve_adv_data_by_type(adv, total, type, &len);
        for (int i = 0; p && i + 1 < len; i += 2) hid |= ((p[i] | (p[i + 1] << 8)) == kHidServiceUuid);
    }
    d.hid = hid;

    std::lock_guard<std::mutex> lk(s_found_mtx);
    for (auto& e : s_found) {
        if (memcmp(e.bda, d.bda, 6) == 0) {
            e.rssi = std::max(e.rssi, d.rssi);
            e.hid |= d.hid;
            if (!e.appearance) e.appearance = d.appearance;
            if (!e.name[0] && d.name[0]) memcpy(e.name, d.name, sizeof(d.name));
            return;
        }
    }
    if (s_found.size() < 40) s_found.push_back(d);
}

void gapCallback(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t* param)
{
    switch (event) {
        case ESP_GAP_BLE_SCAN_PARAM_SET_COMPLETE_EVT:
            xSemaphoreGive(s_scan_param);
            break;
        case ESP_GAP_BLE_SCAN_RESULT_EVT:
            if (param->scan_rst.search_evt == ESP_GAP_SEARCH_INQ_RES_EVT) {
                handleAdv(param->scan_rst);
            } else if (param->scan_rst.search_evt == ESP_GAP_SEARCH_INQ_CMPL_EVT) {
                xSemaphoreGive(s_scan_done);
            }
            break;
        case ESP_GAP_BLE_SEC_REQ_EVT:
            esp_ble_gap_security_rsp(param->ble_security.ble_req.bd_addr, true);
            break;
        case ESP_GAP_BLE_PASSKEY_NOTIF_EVT:
            // We display, the keyboard user types the number followed by Enter.
            s_passkey = param->ble_security.key_notif.passkey;
            ESP_LOGI(kTag, "passkey %06lu", static_cast<unsigned long>(s_passkey.load()));
            changed();
            break;
        case ESP_GAP_BLE_NC_REQ_EVT:
            esp_ble_confirm_reply(param->ble_security.key_notif.bd_addr, true);
            break;
        case ESP_GAP_BLE_PASSKEY_REQ_EVT:
            esp_ble_passkey_reply(param->ble_security.ble_req.bd_addr, false, 0);
            break;
        case ESP_GAP_BLE_AUTH_CMPL_EVT: {
            const auto& a = param->ble_security.auth_cmpl;
            s_passkey = 0;
            if (!a.success) {
                char buf[48];
                snprintf(buf, sizeof(buf), "ペアリング失敗 (0x%x)", a.fail_reason);
                setError(buf);
                ESP_LOGW(kTag, "auth failed 0x%x", a.fail_reason);
                s_auth_failed = true;
                // esp_hidh may still report the device as open; drop the link so CLOSE resets our state.
                esp_ble_gap_disconnect(const_cast<uint8_t*>(a.bd_addr));
            }
            changed();
            break;
        }
        default:
            break;
    }
}

void hidhCallback(void*, esp_event_base_t, int32_t id, void* event_data)
{
    auto* p = static_cast<esp_hidh_event_data_t*>(event_data);
    switch (static_cast<esp_hidh_event_t>(id)) {
        case ESP_HIDH_OPEN_EVENT:
            if (p->open.status == ESP_OK) ESP_LOGI(kTag, "open: %s", esp_hidh_dev_name_get(p->open.dev));
            break;
        case ESP_HIDH_INPUT_EVENT:
            if (p->input.usage == ESP_HID_USAGE_KEYBOARD) input::processReport(p->input.data, p->input.length);
            break;
        case ESP_HIDH_BATTERY_EVENT:
            s_battery = p->battery.level;
            changed();
            break;
        case ESP_HIDH_CLOSE_EVENT: {
            // p->close.dev is still valid here; esp_hidh frees it after this callback returns.
            ESP_LOGI(kTag, "closed (reason %d)", p->close.reason);
            const uint8_t* bda = esp_hidh_dev_bda_get(p->close.dev);
            bool was_current = false;
            {
                std::lock_guard<std::mutex> lk(s_dev_mtx);
                if (s_target_active && bda && memcmp(bda, s_target_bda, 6) == 0) s_target_lost = true;
                if (s_dev && (p->close.dev == s_dev || (bda && memcmp(bda, s_dev_bda, 6) == 0))) {
                    s_dev = nullptr;
                    was_current = true;
                }
            }
            if (was_current) {
                if (s_state == State::Connected) s_state = State::Idle;  // Connecting: connectLocked decides
                s_battery = -1;
                input::releaseAll();
                changed();
            }
            break;
        }
        default:
            break;
    }
}

std::vector<Device> scanLocked(uint32_t seconds)
{
    {
        std::lock_guard<std::mutex> lk(s_found_mtx);
        s_found.clear();
    }
    s_state = State::Scanning;
    changed();
    esp_ble_scan_params_t params = {};
    params.scan_type = BLE_SCAN_TYPE_ACTIVE;
    params.own_addr_type = BLE_ADDR_TYPE_PUBLIC;
    params.scan_filter_policy = BLE_SCAN_FILTER_ALLOW_ALL;
    params.scan_interval = 0x50;
    params.scan_window = 0x30;
    params.scan_duplicate = BLE_SCAN_DUPLICATE_DISABLE;
    xSemaphoreTake(s_scan_param, 0);
    xSemaphoreTake(s_scan_done, 0);
    if (esp_ble_gap_set_scan_params(&params) == ESP_OK) {
        xSemaphoreTake(s_scan_param, pdMS_TO_TICKS(1000));
        if (esp_ble_gap_start_scanning(seconds) == ESP_OK) {
            xSemaphoreTake(s_scan_done, pdMS_TO_TICKS((seconds + 3) * 1000));
        }
    }
    if (s_state == State::Scanning) s_state = currentAlive() ? State::Connected : State::Idle;
    changed();
    std::lock_guard<std::mutex> lk(s_found_mtx);
    std::vector<Device> out = s_found;
    std::sort(out.begin(), out.end(), [](const Device& a, const Device& b) {
        if (a.hid != b.hid) return a.hid;
        return a.rssi > b.rssi;
    });
    return out;
}

bool connectLocked(const Device& d)
{
    {
        std::lock_guard<std::mutex> lk(s_dev_mtx);
        memcpy(s_target_bda, d.bda, 6);
        s_target_active = true;
        s_target_lost = false;
    }
    s_auth_failed = false;
    s_state = State::Connecting;
    s_passkey = 0;
    setError("");
    changed();
    esp_hidh_dev_t* dev = esp_hidh_dev_open(const_cast<uint8_t*>(d.bda), ESP_HID_TRANSPORT_BLE, d.addr_type);
    bool lost;
    {
        std::lock_guard<std::mutex> lk(s_dev_mtx);
        lost = s_target_lost;
        s_target_active = false;
    }
    const bool alive = dev && esp_hidh_dev_exists(dev);
    if (!alive || lost || s_auth_failed) {
        if (alive) esp_hidh_dev_close(dev);
        // A keyboard that was already connected (pairing another one from the menu) keeps working.
        s_state = currentAlive() ? State::Connected : State::Idle;
        s_passkey = 0;
        {
            std::lock_guard<std::mutex> lk(s_info_mtx);
            if (s_error.empty()) s_error = lost ? "接続が途中で切れました" : "接続できませんでした";
        }
        changed();
        return false;
    }
    esp_hidh_dev_t* old;
    {
        std::lock_guard<std::mutex> lk(s_dev_mtx);
        old = s_dev;
        s_dev = dev;
        memcpy(s_dev_bda, d.bda, 6);
    }
    if (old && old != dev && esp_hidh_dev_exists(old)) esp_hidh_dev_close(old);  // one keyboard at a time
    {
        std::lock_guard<std::mutex> lk(s_info_mtx);
        const char* n = esp_hidh_dev_name_get(dev);
        s_name = (n && *n) ? n : d.name;
        s_error.clear();
    }
    settings::Keyboard kb{};
    memcpy(kb.bda, d.bda, 6);
    kb.addr_type = d.addr_type;
    strncpy(kb.name, deviceName().c_str(), sizeof(kb.name) - 1);
    settings::keyboardSet(kb);
    s_passkey = 0;
    s_state = State::Connected;
    changed();
    return true;
}

void bleTask(void*)
{
    for (;;) {
        Request req;
        if (xQueueReceive(s_requests, &req, pdMS_TO_TICKS(1500)) == pdTRUE) {
            xSemaphoreTake(s_op_mtx, portMAX_DELAY);
            s_done_ok = connectLocked(req.dev);
            s_done_ticket = req.ticket;
            xSemaphoreGive(s_op_mtx);
            changed();
            continue;
        }
        // Auto-reconnect to the saved keyboard: it advertises again after a key press.
        settings::Keyboard saved;
        if (!s_auto || s_state != State::Idle || !settings::keyboardGet(saved)) continue;
        xSemaphoreTake(s_op_mtx, portMAX_DELAY);
        auto found = scanLocked(4);
        for (const auto& d : found) {
            const bool same_addr = memcmp(d.bda, saved.bda, 6) == 0;
            const bool same_name = d.hid && saved.name[0] && strncmp(d.name, saved.name, sizeof(saved.name)) == 0;
            if (same_addr || same_name) {
                connectLocked(d);
                break;
            }
        }
        xSemaphoreGive(s_op_mtx);
    }
}

}  // namespace

bool start(std::function<void()> on_change)
{
    s_on_change = std::move(on_change);
    s_op_mtx = xSemaphoreCreateMutex();
    s_scan_param = xSemaphoreCreateBinary();
    s_scan_done = xSemaphoreCreateBinary();
    s_requests = xQueueCreate(2, sizeof(Request));

    esp_err_t err = esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) ESP_LOGW(kTag, "mem release: %s", esp_err_to_name(err));
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    if ((err = esp_bt_controller_init(&bt_cfg)) != ESP_OK ||
        (err = esp_bt_controller_enable(ESP_BT_MODE_BLE)) != ESP_OK ||
        (err = esp_bluedroid_init()) != ESP_OK || (err = esp_bluedroid_enable()) != ESP_OK) {
        ESP_LOGE(kTag, "bt init failed: %s", esp_err_to_name(err));
        setError("Bluetooth の初期化に失敗");
        return false;
    }
    esp_ble_gap_register_callback(gapCallback);

    // Secure Connections + MITM + bonding; we can display a passkey but not enter one.
    esp_ble_auth_req_t auth = ESP_LE_AUTH_REQ_SC_MITM_BOND;
    esp_ble_io_cap_t iocap = ESP_IO_CAP_OUT;
    uint8_t key_size = 16;
    uint8_t keys = ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK;
    esp_ble_gap_set_security_param(ESP_BLE_SM_AUTHEN_REQ_MODE, &auth, sizeof(auth));
    esp_ble_gap_set_security_param(ESP_BLE_SM_IOCAP_MODE, &iocap, sizeof(iocap));
    esp_ble_gap_set_security_param(ESP_BLE_SM_MAX_KEY_SIZE, &key_size, sizeof(key_size));
    esp_ble_gap_set_security_param(ESP_BLE_SM_SET_INIT_KEY, &keys, sizeof(keys));
    esp_ble_gap_set_security_param(ESP_BLE_SM_SET_RSP_KEY, &keys, sizeof(keys));

    esp_ble_gattc_register_callback(esp_hidh_gattc_event_handler);
    esp_hidh_config_t cfg = {};
    cfg.callback = hidhCallback;
    cfg.event_stack_size = 4096;
    cfg.callback_arg = nullptr;
    if ((err = esp_hidh_init(&cfg)) != ESP_OK) {
        ESP_LOGE(kTag, "hidh init failed: %s", esp_err_to_name(err));
        setError("HID ホストの初期化に失敗");
        return false;
    }
    s_state = State::Idle;
    xTaskCreatePinnedToCore(bleTask, "blekbd", 6144, nullptr, 3, nullptr, 0);
    changed();
    return true;
}

State state() { return s_state; }

std::string deviceName()
{
    std::lock_guard<std::mutex> lk(s_info_mtx);
    return s_name;
}

int batteryLevel() { return s_battery; }
uint32_t passkey() { return s_passkey; }

std::string lastError()
{
    std::lock_guard<std::mutex> lk(s_info_mtx);
    return s_error;
}

std::vector<Device> scan(uint32_t seconds, bool* busy)
{
    if (busy) *busy = false;
    if (s_state == State::Off) return {};
    // A connection attempt can take a while (passkey entry); don't freeze the UI forever if the
    // Bluetooth stack never finishes one.
    if (xSemaphoreTake(s_op_mtx, pdMS_TO_TICKS(45000)) != pdTRUE) {
        if (busy) *busy = true;
        return {};
    }
    auto out = scanLocked(seconds);
    xSemaphoreGive(s_op_mtx);
    return out;
}

uint32_t connectAsync(const Device& dev)
{
    if (!s_requests) return 0;
    Request r{dev, s_next_ticket++};
    if (xQueueSend(s_requests, &r, 0) != pdTRUE) return 0;
    return r.ticket;
}

bool connectResult(uint32_t ticket, bool& ok)
{
    if (ticket == 0 || s_done_ticket != ticket) return false;
    ok = s_done_ok;
    return true;
}

void forget()
{
    settings::Keyboard saved;
    if (settings::keyboardGet(saved)) esp_ble_remove_bond_device(saved.bda);
    settings::keyboardClear();
    esp_hidh_dev_t* dev;
    {
        std::lock_guard<std::mutex> lk(s_dev_mtx);
        dev = s_dev;
    }
    if (dev && esp_hidh_dev_exists(dev)) esp_hidh_dev_close(dev);
}

void setAutoReconnect(bool on) { s_auto = on; }

}  // namespace blekbd
