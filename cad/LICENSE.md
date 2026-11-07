# Licence of the enclosure models

The enclosure in this repository is an adaptation of **"The PDA Terminal" / phone-enclosure by Un Kyu Lee**
(https://github.com/unkyulee/phone-enclosure), licensed under the
**Creative Commons Attribution-NonCommercial 4.0 International licence (CC BY-NC 4.0)**,
https://creativecommons.org/licenses/by-nc/4.0/ (legal code: https://creativecommons.org/licenses/by-nc/4.0/legalcode).

The following files contain or show geometry adapted from that work and are licensed under the same
**CC BY-NC 4.0** licence (non-commercial use only), not under the repository's MIT License:

- `cad/out/` (STL files, assembly data, build log, print report)
- `cad/3mf/` (print plates)
- `cad/renders/`
- `docs/images/` (renders and figures of the enclosure)

Attribution: "PaperDIY PDA Terminal enclosure" by Tsuyoshi Otake, adapted from "The PDA Terminal" / phone-enclosure by
Un Kyu Lee, CC BY-NC 4.0. The changes made to the original are listed in [README.md](README.md#changes-vs-the-original-for-the-licence-indicate-changes).

The scripts that build these files from the original STLs (`cad/src/`, `cad/tools/`, `docs/*.py`, `docs/render/`) are
our own code under the MIT License (see [../LICENSE](../LICENSE)). They download the original STLs at build time; the
original files are not part of this repository. Running them produces adapted material, which is again CC BY-NC 4.0.

The PaperDIY dimensions come from M5Stack's published drawing and structure files
([m5stack/M5_Hardware](https://github.com/m5stack/M5_Hardware), K159 / K159-B); M5Stack and PaperDIY are names of
M5Stack. Sugatsune and HG-MF08 are names of Sugatsune Kogyo; CACOE is a keyboard brand. This project is not affiliated
with any of them.

---

## 筐体データのライセンス（日本語）

筐体は Un Kyu Lee さんの「The PDA Terminal / phone-enclosure」（CC BY-NC 4.0）の改変物です。`cad/out/`、`cad/3mf/`、
`cad/renders/`、`docs/images/` は元の作品の形を含む（または描いた）ものなので、リポジトリの MIT ライセンスではなく
**CC BY-NC 4.0（非営利のみ）** です。これらを作るスクリプトは MIT ライセンスです。
