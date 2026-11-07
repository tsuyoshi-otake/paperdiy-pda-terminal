# paperdiy-term-merged.bin

Bootloader (0x0) + partition table (0x8000) + app (0x20000) in one image: write it at **0x0**.

| | |
| --- | --- |
| SHA-256 | `4b35ec3f51e49259cf17f0d215e99adc91da5df0a4c44100b53a8357a483868c` (also in `SHA256SUMS`) |
| Firmware version | 0.3.0 (`firmware/version.txt`) |
| ESP-IDF | **v5.5.6** (tag, commit `880a203a`), target esp32s3 |
| Toolchain | xtensa-esp-elf `esp-14.2.0_20260121` (the one v5.5.6 installs) |
| Dependencies | `fetch_deps.sh`: M5GFX `7cb26b44` (0.2.36), M5Unified `44952cb8` (0.2.29), libssh2 `a312b433` (1.11.1) |
| Build | `./fetch_deps.sh && idf.py build && idf.py merge-bin -o paperdiy-term-merged.bin` (output in `build/`) |

`CONFIG_APP_REPRODUCIBLE_BUILD=y` keeps dates, times and build paths out of the image. 0.2.0 was built in two different
directories, from a fresh clone and in the `espressif/idf:v5.5.6` container on GitHub Actions, all byte-identical; the
`firmware` job of the workflow rebuilds every version in that container and compares the result with this file, and
`make firmware` / `make firmware-docker` at the repository root do the same.

On a PaperDIY: 0.2.0 booted and drew its screen, but upside down with the USB-C end on the left (the way the kit sits in
the enclosure); 0.2.1 turns the landscape screen the other way round. 0.3.0 pairs on its own with a keyboard waiting to
be paired when none is connected.
