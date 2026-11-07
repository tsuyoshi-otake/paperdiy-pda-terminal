# PaperDIY PDA Terminal

M5Stack PaperDIY（4.7 型 e-paper、ESP32-S3）を画面に、CACOE キーボードを BLE でつないだ、PDA 風クラムシェルの SSH 端末です。Un Kyu Lee さんの [phone-enclosure](https://github.com/unkyulee/phone-enclosure)（Boox Palma 2 + CACOE キーボード）を元にしています。

![完成予想（開いたところ）](docs/images/render_open.png)

<p align="center"><img src="docs/images/render_closed.png" width="49%" alt="完成予想（閉じたところ）"> <img src="docs/images/render_back.png" width="49%" alt="完成予想（背面のヒンジ）"></p>

完成予想のレンダリングです。筐体は `cad/out` の STL を組み立てた状態で描いています。PaperDIY は Complete Kit のケースに入れたまま中空の薄い蓋に入れ、画面の窓のある化粧パネルで押さえてねじ 6 本で留めます。ボタンはパネルの切り欠きから直接押せて、USB-C は左端の穴から直接挿します（あとからメス端子に替えるときは蓋の左端の小片だけを刷り直します）。閉じた全体の高さは手前 24.6 mm・奥 27.2 mm で、蓋の手前の留めツメがトレイに掛かって閉じたままになります。ヒンジは背面に埋め込んだ市販のトルクヒンジ（スガツネ HG-MF08 × 2）で、好きな角度で止まり、上にかぶせたカバーで外からは筒だけが見えます。キーボードは CACOE の代わりの簡易モデル、画面の表示はイメージです。

**色の組み合わせ**（黒だけ・カーキだけ・ミックス）：

<p align="center"><img src="docs/images/render_open_black.png" width="32%" alt="黒だけ"> <img src="docs/images/render_open_khaki.png" width="32%" alt="カーキだけ"> <img src="docs/images/render_open_mix.png" width="32%" alt="ミックス（蓋がカーキ、トレイと化粧パネルが黒）"></p>

> **試作段階です。** ファームはビルド（同じソースから同じバイナリができる再現可能ビルド）とホスト上のテストまで、筐体はデータ上のチェックとスライサーでの検査まで済んでいます。実機での動作確認、印刷、仮組みはまだです。

## 作り方

<p align="center"><img src="docs/images/render_exploded.png" width="70%" alt="分解図"></p>

**部品表・印刷設定・組み立て手順は [`cad/ASSEMBLY_ja.md`](cad/ASSEMBLY_ja.md)** にあります（部品表の CSV は [`cad/bom.csv`](cad/bom.csv)）。おおまかな流れは次のとおりです。

1. 部品を買う前に、CACOE が BLE キーボードとして見えるか、キーボードの重さと厚さを確かめる
2. `cad/3mf/plate0_test_coupons.3mf`（約 20 分）を刷って、ヒンジ・蟻ほぞ・留めツメのはめあいを確かめる
3. 本番の 3 枚（蓋・トレイ・化粧パネル、約 3 時間 30 分・PLA 約 140 g、Bambu Lab A1 mini）を刷る
4. ファームを書き込んでから組み立てる。PaperDIY は Complete Kit のケースに入れたまま使い、ねじは M2×8 皿タッピング 14 本（ヒンジ 8、化粧パネル 6）だけ

| フォルダ | 内容 |
| --- | --- |
| [`firmware/`](firmware/) | PaperDIY 用ファームウェア（ESP-IDF v5.5.6）。BLE キーボードのペアリング、Wi-Fi 設定、SSH ターミナル |
| [`cad/`](cad/) | 3D プリント用の筐体データ（[概要](cad/README_ja.md)、[組み立て](cad/ASSEMBLY_ja.md)、[英語の詳細](cad/README.md)） |
| [`docs/`](docs/) | README の画像と、それを描くスクリプト |
| `Makefile`、[`.github/workflows/`](.github/workflows/) | 全部を作り直すコマンドと、push のたびに作り直して確かめる CI |

ビルド済みのファームは [`firmware/prebuilt/`](firmware/prebuilt/) にあります。書き込み方は [`firmware/README.md`](firmware/README.md) を見てください。

## 実機で確かめること

1. CACOE が BLE の HID キーボードとして見えるか（スマホの nRF Connect などで、HID サービス 0x1812 を広告しているか）。ESP32-S3 は Bluetooth Classic に対応しないため、BLE で見えなければつながりません
2. CACOE の重さと寸法。76 g 以上なら蓋をどこまで開いても後ろに倒れません。厚さ（キートップまで）は蓋の高さを決めるので、測って `cad/src/params.py` の `KB_TOP_Z` に入れます（いまは 11.5 mm を想定）。幅と奥行きはトレイを詰めるのに使います
3. CACOE をトレイに置いて、元からある開口から充電ケーブルを挿せるか、スイッチに届くか（充電ケーブルを挿したままだと蓋は 95° まで）
4. PaperDIY 内蔵の 140 mAh でどれくらい使えるか（足りなければモバイルバッテリー）
5. 試し刷りで、ヒンジの筒の太さ（公表値がないので 5.5 mm と仮定）、留めツメの固さ、はめあい

## 作り直す・同じものができるか確かめる

```bash
make setup      # Python のパッケージ（バージョン固定）
make verify     # 元データを固定のコミットで取得 → STL と 3MF を作り直し → コミット済みのものと比べる
make report     # 印刷時間・重さ・スライサーの警告・壁の厚さ・倒れやすさ（PrusaSlicer が要る）
make test       # ファームの端末エミュレータのテスト（g++ と pyte）
make firmware   # ESP-IDF v5.5.6 でビルドして prebuilt/ と 1 バイトずつ比べる（Docker なら make firmware-docker）
make render     # README の画像を描き直す（Node.js）
```

- 元データ（phone-enclosure）はコミットと SHA-256 で固定しています。Python のパッケージ、ESP-IDF、ファームの依存ライブラリ、画像を描く npm パッケージもバージョンを固定しています
- 筐体の出力（STL・3MF）は、同じ PC なら 1 バイトも違わないものができます。別の PC では計算の最後の桁の丸めで一部のファイルのバイトが変わることがありますが、形（体積・寸法）は一致します。全ファイルの SHA-256 と体積・寸法を `cad/out/MANIFEST.json` に記録してあり、`make verify` は 0.01 mm / 0.01 % の差まで許して比べます（GitHub Actions でも全ファイルがバイトか形で一致）
- ファームは日時やパスを含めない再現可能ビルドです。ここで 3 か所、GitHub Actions の `espressif/idf:v5.5.6` コンテナで 1 回ビルドして、どれも `prebuilt/` と 1 バイトも違わないバイナリになりました

変更の履歴は [CHANGELOG.md](CHANGELOG.md) にあります。

## ライセンス

- `cad/`：phone-enclosure（Un Kyu Lee、[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)）の改変物なので、同じ **CC BY-NC 4.0（非営利のみ）** です。変更点は [`cad/README.md`](cad/README.md) にあります。
- `firmware/`：まだ決めていません。使っているライブラリ（M5GFX、M5Unified：MIT、libssh2：BSD-3-Clause、ESP-IDF：Apache-2.0）はビルド時に取得します。
