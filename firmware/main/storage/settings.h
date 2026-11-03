// Persistent settings in NVS: Wi-Fi networks, SSH profiles, keyboard, known hosts, display prefs.
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace settings {

struct WifiNet {
    char ssid[33];
    char pass[65];
};

struct SshProfile {
    char name[24];
    char host[64];
    uint16_t port;
    char user[32];
    char pass[64];     // empty = ask every time
    char keyfile[64];  // empty = no public key auth (path on microSD, e.g. /sd/id_ecdsa)
};

struct Keyboard {
    uint8_t bda[6];
    uint8_t addr_type;
    char name[32];
};

struct Prefs {
    uint8_t font_px;     // 16 or 24
    uint8_t rotate180;   // flip the screen when the lid is mounted upside down
};

constexpr int kMaxWifi = 5;
constexpr int kMaxSsh = 8;

void init();

std::vector<WifiNet> wifiList();          // most recently used first
void wifiSave(const WifiNet& net);        // insert or move to front
void wifiRemove(const std::string& ssid);

std::vector<SshProfile> sshList();
void sshSave(int index, const SshProfile& p);  // index < 0 appends
void sshRemove(int index);

bool keyboardGet(Keyboard& out);
void keyboardSet(const Keyboard& kb);
void keyboardClear();

Prefs prefs();
void prefsSet(const Prefs& p);

bool knownHostGet(const std::string& host_port, std::string& fingerprint);
void knownHostSet(const std::string& host_port, const std::string& fingerprint);

}  // namespace settings
