// HID keyboard reports -> key events (US layout), typematic repeat, and the shared key queue.
#pragma once

#include <cstddef>
#include <cstdint>

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

namespace input {

enum Key : uint16_t {
    kKeyNone = 0,
    kKeyChar = 1,  // ev.ch holds the character (already shifted)
    kKeyEnter = 0x100,
    kKeyEscape,
    kKeyBackspace,
    kKeyTab,
    kKeyUp,
    kKeyDown,
    kKeyLeft,
    kKeyRight,
    kKeyHome,
    kKeyEnd,
    kKeyPageUp,
    kKeyPageDown,
    kKeyInsert,
    kKeyDelete,
    kKeyF1,
    kKeyF12 = kKeyF1 + 11,
    kKeyButtonA = 0x200,  // PaperDIY side buttons
    kKeyButtonB,
};

enum Mod : uint8_t { kModCtrl = 1, kModShift = 2, kModAlt = 4, kModGui = 8 };

struct KeyEvent {
    uint16_t key;
    uint8_t mods;
    uint32_t ch;
};

void init();
QueueHandle_t queue();
void post(const KeyEvent& ev);
// Standard keyboard input report: [modifiers, reserved, key1..key6] (7-byte form without reserved also accepted)
void processReport(const uint8_t* data, size_t len);
void releaseAll();

}  // namespace input
