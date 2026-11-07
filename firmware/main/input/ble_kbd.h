// BLE HID keyboard host (Bluedroid + ESP-IDF esp_hidh). ESP32-S3 is BLE-only, so the keyboard
// must expose HID over GATT. Pairing uses passkey entry: the passkey is shown on the e-paper
// and typed on the keyboard.
//
// While no keyboard is connected, a background task scans every few seconds: it reconnects the
// saved keyboard when that one advertises, and otherwise pairs with a keyboard nearby that is
// waiting to be paired (discoverable, keyboard appearance or HID service, close by).
#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <vector>

namespace blekbd {

enum class State : uint8_t { Off, Idle, Scanning, Connecting, Connected };

struct Device {
    uint8_t bda[6];
    uint8_t addr_type;
    int rssi;
    uint16_t appearance;
    bool hid;       // advertises the HID service or a keyboard appearance
    uint8_t flags;  // advertising Flags (bit 0: LE limited, bit 1: LE general discoverable)
    char name[32];
};

bool start(std::function<void()> on_change);
State state();
std::string deviceName();
std::string targetName();  // the keyboard being connected (State::Connecting)
int batteryLevel();       // -1 when unknown
uint32_t passkey();       // non-zero while the keyboard user has to type it
std::string lastError();

// Blocking; HID devices first. *busy is set when Bluetooth stayed busy and no scan ran.
std::vector<Device> scan(uint32_t seconds, bool* busy = nullptr);
// Pairs/connects in the background. Returns a ticket (0 = not queued) for connectResult().
uint32_t connectAsync(const Device& dev);
bool connectResult(uint32_t ticket, bool& ok);  // true once that attempt has finished
void forget();                                  // remove the bond and the saved keyboard
void setAutoReconnect(bool on);
void setAutoPair(bool on);  // pair on its own with a keyboard waiting to be paired (default on)

}  // namespace blekbd
