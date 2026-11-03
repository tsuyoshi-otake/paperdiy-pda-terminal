#include "keyboard.h"

#include <cstring>

#include "esp_timer.h"
#include "freertos/task.h"

namespace input {
namespace {

constexpr int64_t kRepeatDelayUs = 450 * 1000;
constexpr int64_t kRepeatIntervalUs = 45 * 1000;

QueueHandle_t s_queue = nullptr;
portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;
uint8_t s_prev_keys[6] = {};
uint8_t s_mods = 0;
bool s_caps = false;
uint8_t s_repeat_usage = 0;
int64_t s_repeat_next_us = 0;

uint8_t modsFromHid(uint8_t m)
{
    uint8_t out = 0;
    if (m & 0x11) out |= kModCtrl;
    if (m & 0x22) out |= kModShift;
    if (m & 0x44) out |= kModAlt;
    if (m & 0x88) out |= kModGui;
    return out;
}

KeyEvent translate(uint8_t usage, uint8_t hid_mods, bool caps)
{
    KeyEvent ev{kKeyNone, modsFromHid(hid_mods), 0};
    const bool shift = ev.mods & kModShift;
    auto chr = [&](char normal, char shifted) {
        ev.key = kKeyChar;
        ev.ch = static_cast<uint8_t>(shift ? shifted : normal);
    };
    if (usage >= 0x04 && usage <= 0x1D) {
        char c = static_cast<char>('a' + usage - 0x04);
        if (shift != caps) c = static_cast<char>(c - 'a' + 'A');
        ev.key = kKeyChar;
        ev.ch = static_cast<uint8_t>(c);
        return ev;
    }
    if (usage >= 0x1E && usage <= 0x27) {
        static const char normal[] = "1234567890";
        static const char shifted[] = "!@#$%^&*()";
        chr(normal[usage - 0x1E], shifted[usage - 0x1E]);
        return ev;
    }
    if (usage >= 0x3A && usage <= 0x45) {
        ev.key = static_cast<uint16_t>(kKeyF1 + (usage - 0x3A));
        return ev;
    }
    if (usage >= 0x59 && usage <= 0x61) {  // keypad 1..9
        ev.key = kKeyChar;
        ev.ch = static_cast<uint8_t>('1' + usage - 0x59);
        return ev;
    }
    switch (usage) {
        case 0x28: case 0x58: ev.key = kKeyEnter; break;
        case 0x29: ev.key = kKeyEscape; break;
        case 0x2A: ev.key = kKeyBackspace; break;
        case 0x2B: ev.key = kKeyTab; break;
        case 0x2C: chr(' ', ' '); break;
        case 0x2D: chr('-', '_'); break;
        case 0x2E: chr('=', '+'); break;
        case 0x2F: chr('[', '{'); break;
        case 0x30: chr(']', '}'); break;
        case 0x31: chr('\\', '|'); break;
        case 0x32: chr('#', '~'); break;
        case 0x33: chr(';', ':'); break;
        case 0x34: chr('\'', '"'); break;
        case 0x35: chr('`', '~'); break;
        case 0x36: chr(',', '<'); break;
        case 0x37: chr('.', '>'); break;
        case 0x38: chr('/', '?'); break;
        case 0x49: ev.key = kKeyInsert; break;
        case 0x4A: ev.key = kKeyHome; break;
        case 0x4B: ev.key = kKeyPageUp; break;
        case 0x4C: ev.key = kKeyDelete; break;
        case 0x4D: ev.key = kKeyEnd; break;
        case 0x4E: ev.key = kKeyPageDown; break;
        case 0x4F: ev.key = kKeyRight; break;
        case 0x50: ev.key = kKeyLeft; break;
        case 0x51: ev.key = kKeyDown; break;
        case 0x52: ev.key = kKeyUp; break;
        case 0x54: chr('/', '/'); break;
        case 0x55: chr('*', '*'); break;
        case 0x56: chr('-', '-'); break;
        case 0x57: chr('+', '+'); break;
        case 0x62: chr('0', '0'); break;
        case 0x63: chr('.', '.'); break;
        case 0x64: chr('\\', '|'); break;  // ISO key next to left shift
        default: break;
    }
    return ev;
}

bool repeatable(uint8_t usage)
{
    return usage != 0x39 && usage != 0x29 && !(usage >= 0x3A && usage <= 0x45) && usage != 0x58 && usage != 0x28;
}

void repeatTask(void*)
{
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(10));
        KeyEvent ev{kKeyNone, 0, 0};
        const int64_t now = esp_timer_get_time();
        portENTER_CRITICAL(&s_mux);
        if (s_repeat_usage && now >= s_repeat_next_us) {
            ev = translate(s_repeat_usage, s_mods, s_caps);
            s_repeat_next_us = now + kRepeatIntervalUs;
        }
        portEXIT_CRITICAL(&s_mux);
        if (ev.key != kKeyNone && uxQueueMessagesWaiting(s_queue) < 4) post(ev);
    }
}

}  // namespace

void init()
{
    if (s_queue) return;
    s_queue = xQueueCreate(32, sizeof(KeyEvent));
    xTaskCreate(repeatTask, "keyrepeat", 3072, nullptr, 5, nullptr);
}

QueueHandle_t queue() { return s_queue; }

void post(const KeyEvent& ev)
{
    if (s_queue) xQueueSend(s_queue, &ev, 0);
}

void processReport(const uint8_t* data, size_t len)
{
    if (len < 3) return;
    const uint8_t mods = data[0];
    uint8_t keys[6] = {};
    const uint8_t* src = (len >= 8) ? data + 2 : data + 1;
    const size_t n = (len >= 8) ? 6 : len - 1;
    memcpy(keys, src, n < 6 ? n : 6);
    if (keys[0] == 0x01) return;  // phantom state (rollover error)

    KeyEvent out[6];
    int nout = 0;
    portENTER_CRITICAL(&s_mux);
    s_mods = mods;
    for (int i = 0; i < 6; ++i) {
        const uint8_t k = keys[i];
        if (k == 0) continue;
        bool was = false;
        for (int j = 0; j < 6; ++j) was |= (s_prev_keys[j] == k);
        if (was) continue;
        if (k == 0x39) {
            s_caps = !s_caps;
            continue;
        }
        KeyEvent ev = translate(k, mods, s_caps);
        if (ev.key != kKeyNone) out[nout++] = ev;
        if (repeatable(k)) {
            s_repeat_usage = k;
            s_repeat_next_us = esp_timer_get_time() + kRepeatDelayUs;
        }
    }
    bool still_down = false;
    for (int i = 0; i < 6; ++i) still_down |= (keys[i] == s_repeat_usage && keys[i] != 0);
    if (!still_down) s_repeat_usage = 0;
    memcpy(s_prev_keys, keys, sizeof(keys));
    portEXIT_CRITICAL(&s_mux);
    for (int i = 0; i < nout; ++i) post(out[i]);
}

void releaseAll()
{
    portENTER_CRITICAL(&s_mux);
    memset(s_prev_keys, 0, sizeof(s_prev_keys));
    s_mods = 0;
    s_repeat_usage = 0;
    portEXIT_CRITICAL(&s_mux);
}

}  // namespace input
