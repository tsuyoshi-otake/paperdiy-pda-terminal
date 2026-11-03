# PaperDIY PDA Terminal

M5Stack PaperDIY（4.7 型 e-paper、ESP32-S3）を画面に、CACOE キーボードを BLE でつないだ、PDA 風クラムシェルの SSH 端末です。Un Kyu Lee さんの [phone-enclosure](https://github.com/unkyulee/phone-enclosure)（Boox Palma 2 + CACOE キーボード）を元にしています。

![完成予想（開いたところ）](docs/images/render_open.png)

<p align="center"><img src="docs/images/render_closed.png" width="49%" alt="完成予想（閉じたところ）"> <img src="docs/images/render_back.png" width="49%" alt="完成予想（背面のヒンジ）"></p>

完成予想のレンダリングです。筐体は `cad/out` の STL を組み立てた状態で描いています。ヒンジは背面に埋め込んだ市販のトルクヒンジ（スガツネ HG-MF08 × 2）で、好きな角度で止まります。上にケースと同じ色のカバーをかぶせているので、外から見えるのは筒だけです。キーボードは CACOE の代わりの簡易モデル、画面の表示と天面の赤いプレートはイメージです。描き直すときは `docs/render/` で `npm install` と `npm run render` を実行します。

> **試作段階です。** ファームはビルドとホスト上のテストまで、筐体はデータ上のチェックまで済んでいます。実機での動作確認、印刷、仮組みはまだです。

| フォルダ | 内容 |
| --- | --- |
| [`firmware/`](firmware/) | PaperDIY 用ファームウェア（ESP-IDF 5.5）。BLE キーボードのペアリング、Wi-Fi 設定、SSH ターミナル |
| [`cad/`](cad/) | 3D プリント用の筐体データ。Bambu Lab A1 mini（180 mm）に載るよう分割済み |

ビルド済みのファームは [`firmware/prebuilt/`](firmware/prebuilt/) にあります。書き込み方は [`firmware/README.md`](firmware/README.md)、筐体の概要は [`cad/README_ja.md`](cad/README_ja.md)、**部品表・印刷設定・組み立て手順は [`cad/ASSEMBLY_ja.md`](cad/ASSEMBLY_ja.md)** を見てください。

## 実機で確かめること

1. CACOE が BLE の HID キーボードとして見えるか（スマホの nRF Connect などで、HID サービス 0x1812 を広告しているか）。ESP32-S3 は Bluetooth Classic に対応しないため、BLE で見えなければつながりません。
2. CACOE をトレイに置いて、元からある開口から充電ケーブルを挿せるか、スイッチに届くか。
3. PaperDIY の充電電流（USB 電流計で測る）、パネルマウント USB-C のねじ穴の間隔、電池の実寸。

## ライセンス

- `cad/`：phone-enclosure（Un Kyu Lee、[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)）の改変物なので、同じ **CC BY-NC 4.0（非営利のみ）** です。変更点は [`cad/README.md`](cad/README.md) にあります。
- `firmware/`：まだ決めていません。使っているライブラリ（M5GFX、M5Unified：MIT、libssh2：BSD-3-Clause、ESP-IDF：Apache-2.0）はビルド時に取得します。
