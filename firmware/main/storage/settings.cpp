#include "settings.h"

#include <cstring>

#include "esp_log.h"
#include "nvs.h"
#include "nvs_flash.h"

namespace settings {
namespace {

constexpr char kNs[] = "pdterm";
constexpr char kTag[] = "settings";

template <typename T>
std::vector<T> loadList(const char* key)
{
    std::vector<T> out;
    nvs_handle_t h;
    if (nvs_open(kNs, NVS_READONLY, &h) != ESP_OK) return out;
    size_t size = 0;
    if (nvs_get_blob(h, key, nullptr, &size) == ESP_OK && size > 0 && size % sizeof(T) == 0) {
        out.resize(size / sizeof(T));
        if (nvs_get_blob(h, key, out.data(), &size) != ESP_OK) out.clear();
    }
    nvs_close(h);
    return out;
}

template <typename T>
void storeList(const char* key, const std::vector<T>& list)
{
    nvs_handle_t h;
    if (nvs_open(kNs, NVS_READWRITE, &h) != ESP_OK) return;
    if (list.empty()) {
        nvs_erase_key(h, key);
    } else {
        nvs_set_blob(h, key, list.data(), list.size() * sizeof(T));
    }
    nvs_commit(h);
    nvs_close(h);
}

template <typename T>
bool loadBlob(const char* key, T& out)
{
    nvs_handle_t h;
    if (nvs_open(kNs, NVS_READONLY, &h) != ESP_OK) return false;
    size_t size = sizeof(T);
    bool ok = nvs_get_blob(h, key, &out, &size) == ESP_OK && size == sizeof(T);
    nvs_close(h);
    return ok;
}

template <typename T>
void storeBlob(const char* key, const T& v)
{
    nvs_handle_t h;
    if (nvs_open(kNs, NVS_READWRITE, &h) != ESP_OK) return;
    nvs_set_blob(h, key, &v, sizeof(T));
    nvs_commit(h);
    nvs_close(h);
}

// NVS keys are limited to 15 characters, so known hosts are keyed by a hash.
std::string hostKey(const std::string& host_port)
{
    uint32_t h = 2166136261u;
    for (unsigned char c : host_port) {
        h ^= c;
        h *= 16777619u;
    }
    char key[16];
    snprintf(key, sizeof(key), "kh%08lx", static_cast<unsigned long>(h));
    return key;
}

}  // namespace

void init()
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(kTag, "erasing NVS (%s)", esp_err_to_name(err));
        nvs_flash_erase();
        err = nvs_flash_init();
    }
    if (err != ESP_OK) ESP_LOGE(kTag, "nvs init failed: %s", esp_err_to_name(err));
}

std::vector<WifiNet> wifiList() { return loadList<WifiNet>("wifi"); }

void wifiSave(const WifiNet& net)
{
    auto list = wifiList();
    for (auto it = list.begin(); it != list.end(); ++it) {
        if (strcmp(it->ssid, net.ssid) == 0) {
            list.erase(it);
            break;
        }
    }
    list.insert(list.begin(), net);
    if (list.size() > kMaxWifi) list.resize(kMaxWifi);
    storeList("wifi", list);
}

void wifiRemove(const std::string& ssid)
{
    auto list = wifiList();
    for (auto it = list.begin(); it != list.end(); ++it) {
        if (ssid == it->ssid) {
            list.erase(it);
            break;
        }
    }
    storeList("wifi", list);
}

std::vector<SshProfile> sshList() { return loadList<SshProfile>("ssh"); }

void sshSave(int index, const SshProfile& p)
{
    auto list = sshList();
    if (index >= 0 && index < static_cast<int>(list.size())) {
        list[index] = p;
    } else if (list.size() < kMaxSsh) {
        list.push_back(p);
    }
    storeList("ssh", list);
}

void sshRemove(int index)
{
    auto list = sshList();
    if (index >= 0 && index < static_cast<int>(list.size())) list.erase(list.begin() + index);
    storeList("ssh", list);
}

bool keyboardGet(Keyboard& out) { return loadBlob("kbd", out); }
void keyboardSet(const Keyboard& kb) { storeBlob("kbd", kb); }

void keyboardClear()
{
    nvs_handle_t h;
    if (nvs_open(kNs, NVS_READWRITE, &h) != ESP_OK) return;
    nvs_erase_key(h, "kbd");
    nvs_commit(h);
    nvs_close(h);
}

Prefs prefs()
{
    Prefs p{24, 0};
    Prefs stored;
    if (loadBlob("prefs", stored)) p = stored;
    if (p.font_px != 16 && p.font_px != 24) p.font_px = 24;
    return p;
}

void prefsSet(const Prefs& p) { storeBlob("prefs", p); }

bool knownHostGet(const std::string& host_port, std::string& fingerprint)
{
    nvs_handle_t h;
    if (nvs_open(kNs, NVS_READONLY, &h) != ESP_OK) return false;
    char buf[96];
    size_t len = sizeof(buf);
    bool ok = nvs_get_str(h, hostKey(host_port).c_str(), buf, &len) == ESP_OK;
    nvs_close(h);
    if (ok) fingerprint = buf;
    return ok;
}

void knownHostSet(const std::string& host_port, const std::string& fingerprint)
{
    nvs_handle_t h;
    if (nvs_open(kNs, NVS_READWRITE, &h) != ESP_OK) return;
    nvs_set_str(h, hostKey(host_port).c_str(), fingerprint.c_str());
    nvs_commit(h);
    nvs_close(h);
}

}  // namespace settings
