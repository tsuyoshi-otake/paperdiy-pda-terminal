// Wi-Fi station: scan, connect, remember networks (NVS), reconnect when the link drops.
#pragma once

#include <functional>
#include <string>
#include <vector>

namespace wifi {

enum class State : uint8_t { Off, Idle, Connecting, Connected, Failed };

struct Ap {
    std::string ssid;
    int rssi;
    bool secure;
};

bool start(std::function<void()> on_change);
State state();
std::string ssid();
std::string ip();
std::string lastError();

std::vector<Ap> scan();  // blocking, strongest first, de-duplicated by SSID
// Blocking connect; on success the network is saved (most recent first).
bool connect(const std::string& ssid, const std::string& pass, int timeout_ms = 15000);
void autoConnectAsync();  // try saved networks in the background
void disconnect();

}  // namespace wifi
