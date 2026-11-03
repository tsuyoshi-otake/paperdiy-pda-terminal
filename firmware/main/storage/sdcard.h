// microSD on the PaperDIY (SPI: SCK G39, MOSI G38, MISO G40, CS G47, card detect G48).
#pragma once

namespace sdcard {

constexpr char kMountPoint[] = "/sd";

bool inserted();
bool mount();      // safe to call repeatedly
bool mounted();

}  // namespace sdcard
