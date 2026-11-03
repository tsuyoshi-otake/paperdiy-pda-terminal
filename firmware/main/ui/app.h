// Application: text UI on the console screen, terminal mode for SSH sessions.
#pragma once

#include <string>

#include "input/keyboard.h"
#include "storage/settings.h"
#include "term/renderer.h"
#include "term/vt.h"

class App {
public:
    void run();  // never returns

private:
    // console helpers
    void cls(const char* title);
    void say(const std::string& s);
    bool getKey(input::KeyEvent& ev, int timeout_ms);  // false on timeout
    void waitAnyKey(const char* msg = "何かキーを押すと戻ります");
    bool readLine(const std::string& prompt, std::string& out, bool mask = false);
    int readNumber(const std::string& prompt, int max);  // 1..max, or -1 on cancel
    bool confirm(const std::string& question);
    void updateStatus(bool force = false);

    // screens
    void bootWaitForKeyboard();
    void pairingScreen(bool from_menu);
    void mainMenu();
    std::string menuSummary();
    void sshConnectMenu();
    void sshManageMenu();
    bool editProfile(int index);
    void connectProfile(const settings::SshProfile& p);
    void terminalLoop();
    void wifiMenu();
    void wifiConnect(const std::string& ssid, const std::string& pass);
    void keyboardMenu();
    void displayMenu();
    void applyFont(int px);

    std::string encodeKey(const input::KeyEvent& ev, bool app_cursor) const;

    term::Renderer renderer_;
    term::Vt* console_ = nullptr;
    term::Vt* session_ = nullptr;
    settings::Prefs prefs_{};
    int battery_pct_ = -1;
    bool charging_ = false;
};
