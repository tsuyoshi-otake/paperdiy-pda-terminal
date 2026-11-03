// SSH client (libssh2 + mbedTLS): connect, verify the host key (trust on first use),
// authenticate, open an xterm PTY shell and pump data in a background task.
#pragma once

#include <cstddef>
#include <functional>
#include <string>

#include "storage/settings.h"

namespace ssh {

enum class State : uint8_t { Idle, Connecting, Open };

// Interaction during connect(); called from the connecting task (the UI task).
struct Prompter {
    std::function<void(const std::string& msg)> status;
    std::function<bool(const std::string& question)> confirm;  // y/N
    std::function<bool(const std::string& prompt, bool echo, std::string& answer)> ask;
};

void setHandlers(std::function<void(const char*, size_t)> on_data, std::function<void(const std::string&)> on_closed);
bool connect(const settings::SshProfile& profile, int cols, int rows, Prompter& ui, std::string& error);
void write(const char* data, size_t len);
void resize(int cols, int rows);
void close();
State state();
std::string label();  // user@host

}  // namespace ssh
