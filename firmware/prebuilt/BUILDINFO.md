# paperdiy-term-merged.bin / paperdiy-term-app.bin

- `paperdiy-term-merged.bin`: bootloader (0x0) + partition table (0x8000) + app (0x20000) in one image, write it at
  **0x0**. The gap between them (NVS, phy_init) is 0xFF, so this also erases the settings: use it for the first install.
- `paperdiy-term-app.bin`: the app alone, write it at **0x20000** to update and keep the settings (keyboard bond,
  Wi-Fi, SSH hosts, known host keys). The partition table has not changed since 0.1.

| | |
| --- | --- |
| SHA-256 | merged `2a23f0a2efa21b26b4bba16ab16d69b0ba55fe270663f61c666f9733bafa3383`, app `cb743d5ca8b69cbb90721a88c5bea60df5af3c59f933bddec8bb0b3405b9ffb7` (also in `SHA256SUMS`) |
| Firmware version | 0.3.1 (`firmware/version.txt`) |
| ESP-IDF | **v5.5.6** (tag, commit `880a203a`), target esp32s3 |
| Toolchain | xtensa-esp-elf `esp-14.2.0_20260121` (the one v5.5.6 installs) |
| Dependencies | `fetch_deps.sh`: M5GFX `7cb26b44` (0.2.36), M5Unified `44952cb8` (0.2.29), libssh2 `a312b433` (1.11.1) |
| Build | `./fetch_deps.sh && idf.py build && idf.py merge-bin -o paperdiy-term-merged.bin` (output in `build/`; the app is `build/paperdiy_term.bin`) |

`CONFIG_APP_REPRODUCIBLE_BUILD=y` keeps dates, times and build paths out of the image. 0.2.0 was built in two different
directories, from a fresh clone and in the `espressif/idf:v5.5.6` container on GitHub Actions, all byte-identical; the
`firmware` job of the workflow rebuilds every version in that container and compares the results with these files, and
`make firmware` / `make firmware-docker` at the repository root do the same.

On a PaperDIY: 0.2.0 booted and drew its screen, but upside down with the USB-C end on the left (the way the kit sits in
the enclosure); 0.2.1 turns the landscape screen the other way round. 0.3.0 pairs on its own with a keyboard waiting to
be paired when none is connected. With 0.3.0 an SSH login ended in "out of memory"; 0.3.1 keeps one SSH I/O task
with its stack in PSRAM, moves mbedTLS and small mallocs to PSRAM, and gives Wi-Fi fewer internal buffers: free internal RAM
after start went from 24 KB (largest block 16 KB) to 57 KB (31 KB), measured on the PaperDIY.
