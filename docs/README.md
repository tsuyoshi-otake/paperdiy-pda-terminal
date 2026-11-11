# docs/

README と組み立て手順に使っている画像（`images/`）と、それを描くスクリプト、リリースノート（`releases/`、タグごとに 1 ファイル。リリースを出すワークフローが題名と本文に使います）です。画像は `cad/out/` の STL から描いているので、筐体を作り直したら描き直します。

| ファイル | 描くもの | 作り直し方 |
| --- | --- | --- |
| `images/photo_2026-11-11.jpg` | 組み上がった実機の写真（作者が撮影。留めツメを直す前の版） | 写真なので作り直せない |
| `render/`（three.js、ヘッドレス Chromium） | 完成予想（`render_open` / `closed` / `back` / `exploded` / `hinge`、閉じた形を正面・左端から水平に見た `render_front` / `end`、右手前斜めの `render_diag`、開いて左から見た `render_side`）と、黒・カーキ・ミックスの色違い（`render_{open,closed}_{black,khaki,mix}`） | `make render`（Node.js が要る。npm のパッケージと Chromium も取ってくる） |
| `kit_figure.py` | PaperDIY と化粧パネルの取り付け図（`kit_mount.png`） | `python3 docs/kit_figure.py` |
| `snap_figure.py` | 化粧パネルの突起と溝の位置と断面（`panel_snap.png`） | `python3 docs/snap_figure.py` |
| `splice_figure.py` | 分割版の継ぎ板の位置と、継ぎ目の断面（`splice_plates.png`） | `python3 docs/splice_figure.py` |
| `hinge_figure.py` | ヒンジの留め方（`hinge_screws.png`） | `python3 docs/hinge_figure.py` |
| `latch_figure.py` | 留めツメ（`latch.png`） | `python3 docs/latch_figure.py` |
| `../cad/tools/snap_sim.py`（図は `snap_sim_figure.py`） | 留めツメを閉じるシミュレーションの図（`snap_sim.png`）。数値は `cad/out/snap_sim.md` | `cd cad && python3 tools/snap_sim.py --figure ../docs/images/snap_sim.png`（`--gif 名前.gif` で、閉じる動きのアニメーションも出せる） |
| `coupons_figure.py` | 試し刷りの小片（`plate0_coupons.png`） | `python3 docs/coupons_figure.py` |

Python の図は matplotlib と日本語フォント（Noto Sans CJK JP など）が要ります。`make render` はレンダリングと図をまとめて描き直します。

`images/` の画像は筐体（phone-enclosure の改変物）を描いたものなので、ライセンスは [CC BY-NC 4.0](../cad/LICENSE.md) です。スクリプトは MIT ライセンスです。
