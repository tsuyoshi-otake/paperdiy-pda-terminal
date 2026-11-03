# paperdiy-term-merged.bin

Bootloader (0x0) + partition table (0x8000) + app (0x20000) in one image: write it at **0x0**.

| | |
| --- | --- |
| SHA-256 | `21736e9d467bd54c7667bd3141d199bd09ec8e868c4ca1399dc8f5f4df3f3e74` (also in `SHA256SUMS`) |
| Firmware version | 0.2.0 (`firmware/version.txt`) |
| ESP-IDF | **v5.5.6** (tag, commit `880a203a`), target esp32s3 |
| Toolchain | xtensa-esp-elf `esp-14.2.0_20260121` (the one v5.5.6 installs) |
| Dependencies | `fetch_deps.sh`: M5GFX `7cb26b44` (0.2.36), M5Unified `44952cb8` (0.2.29), libssh2 `a312b433` (1.11.1) |
| Build | `./fetch_deps.sh && idf.py build && idf.py merge-bin -o paperdiy-term-merged.bin` (output in `build/`) |

`CONFIG_APP_REPRODUCIBLE_BUILD=y` keeps dates, times and build paths out of the image. This file was built twice,
from two different directories, and both builds were byte-identical. With ESP-IDF v5.5.6 the same sources should give
exactly this file anywhere, including the `espressif/idf:v5.5.6` container (`make firmware-docker` at the repository
root, or the `firmware` job of the GitHub Actions workflow), which compares the result with this file.

Not yet tested on a PaperDIY.
