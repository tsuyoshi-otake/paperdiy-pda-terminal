# PaperDIY Terminal

M5Stack PaperDIY（ESP32-S3、4.7 型 e-paper）を、BLE キーボードで操作する SSH ターミナルにするファームウェアです。PaperDIY PDA Terminal 構想の試作ファームとして作りました。

> **実機では未検証です。** ESP-IDF 5.5 でのビルドと、ターミナル部分のホスト上テスト（vim / less / top / nano / bash / tmux の出力を参照実装 pyte と比較）までは確認済みです。

## できること

- **BLE キーボード**：HID over GATT のキーボードとペアリングして入力（パスキーは e-paper に表示）。次回からは自動で再接続
- **Wi-Fi**：検索して接続、非公開 SSID の手入力、保存済みネットワーク（最大 5 件）への自動接続。ルーターの再起動などで切れても、間隔を空けながらつながるまで再接続
- **SSH**：接続先を最大 8 件保存。パスワード、キーボードインタラクティブ、microSD 上の秘密鍵で認証。ホスト鍵は初回に指紋を確認して保存し、変わったら警告
- **ターミナル**：xterm 互換のサブセット（UTF-8、日本語の全角表示、スクロール領域、代替画面、罫線）。vim、less、top、nano、tmux が動く範囲を想定
- **表示**：24px（80 桁×21 行）と 16px（120 桁×32 行）を切り替え。画面の上下反転

## 必要なもの

- M5Stack PaperDIY（Assembly Kit / Complete Kit）
- BLE（Bluetooth Low Energy）の HID に対応したキーボード。ESP32-S3 は Bluetooth Classic に対応しないため、Classic 専用のキーボードはつながりません
- ESP-IDF 5.5（ビルドする場合）

## 書き込み

### ビルド済みのファームを書く

`prebuilt/paperdiy-term-merged.bin` を 0x0 番地に書き込みます。PaperDIY を USB-C で PC につなぎ、この `firmware/` フォルダで

```bash
python -m esptool --chip esp32s3 -b 460800 write_flash 0x0 prebuilt/paperdiy-term-merged.bin
```

ブラウザの [ESP Tool](https://espressif.github.io/esptool-js/) でも同じファイルを 0x0 に書けます。書き込みモードに入らないときは、電源ボタンを長押ししてダウンロードモードにします。

### ソースからビルドする

```bash
cd firmware
./fetch_deps.sh            # M5GFX / M5Unified / libssh2 を固定リビジョンで取得
. $IDF_PATH/export.sh      # ESP-IDF 5.5
idf.py set-target esp32s3
idf.py build flash monitor
```

## 使い方

### 1. キーボードをつなぐ（初回）

起動するとキーボードの接続画面になります。キーボードがまだ使えないので、PaperDIY の 2 つのボタンで操作します。

1. キーボードをペアリング（接続待ち）の状態にする
2. **ボタンA** で検索
3. 一覧から **ボタンB** で選び、**ボタンA** で接続（一覧の最後の「もう一度検索する / 戻る」で最初の画面に戻れます）
4. 画面に 6 桁の数字が出たら、キーボードでその数字を打って Enter

2 回目以降は、キーボードのキーを押せば自動でつながります。キーボード側のペアリング情報が消えていて再ペアリングが必要になったときは、どの画面にいても下のステータス行に 6 桁の数字が出るので、同じようにキーボードで打って Enter を押します。

### 2. Wi-Fi を設定する

メニューの `3 Wi-Fi を設定する` → `1 ネットワークを検索して接続` で番号とパスワードを入力します。成功したネットワークは保存され、次回から自動で接続します。

### 3. SSH で接続する

メニューの `1 SSH で接続する` で接続先を追加して接続します。初めてのサーバーではホスト鍵の指紋（`SHA256:...`）が出ます。サーバー側で `ssh-keygen -lf /etc/ssh/ssh_host_ecdsa_key.pub` などと照らし合わせてから `y` で保存してください。

### 操作

| 操作 | 動作 |
| --- | --- |
| ボタンA / Ctrl+Alt+M | ターミナルからメニューへ（接続は保ったまま） |
| ボタンB / Ctrl+Alt+R | 画面を全面リフレッシュ（残像を消す） |
| メニューの T / Esc | ターミナルに戻る |
| メニューの 0 | SSH を切断 |
| 電源ボタン 2 回押し | 電源オフ（PaperDIY 本体の機能） |

## 公開鍵認証

libssh2 の mbedTLS 版は **PEM 形式の RSA / ECDSA 鍵**だけを読めます。ED25519 鍵と OpenSSH 新形式（`BEGIN OPENSSH PRIVATE KEY`）は使えません。

```bash
ssh-keygen -t ecdsa -b 256 -m PEM -f id_ecdsa       # 新しく作る
ssh-keygen -p -m PEM -f 既存のRSAかECDSA鍵           # 既存鍵を PEM に変換
```

`id_ecdsa` を microSD のルートに置き、接続先の「鍵ファイル」に `/sd/id_ecdsa` と入れます。公開鍵（`id_ecdsa.pub`）はサーバーの `~/.ssh/authorized_keys` に追加します。

## 対応する SSH サーバー

- 鍵交換は ecdh-sha2-nistp256/384/521 と diffie-hellman 系。curve25519 は使えません（OpenSSH の標準設定なら ecdh-sha2-nistp256 で通ります）
- ホスト鍵は ECDSA か RSA。**ED25519 のホスト鍵しか持たないサーバーにはつながりません**

## 制限と注意

- **日本語は表示のみ**で、入力はできません（IME なし）。キー配列は US
- e-paper なので色は出ません。暗い背景色は白黒反転で表します
- スクロールバック（画面外の履歴）はありません。tmux や less を使ってください
- **保存したパスワードは NVS に暗号化なしで入ります。** 気になる場合はパスワードを保存せず（空欄）、接続のたびに入力するか、公開鍵認証を使ってください
- 高速の部分書き換えを続けると残像が出ます。4 秒ほど操作がないと自動で全面リフレッシュします
- Wi-Fi と BLE を常時使うため、内蔵 140 mAh 電池では長く持ちません

## 構成

| パス | 内容 |
| --- | --- |
| `main/term/vt.*` | VT100 / xterm サブセットの端末エミュレータ |
| `main/term/renderer.*` | e-paper への描画（部分リフレッシュ、罫線、ステータスバー） |
| `main/input/ble_kbd.*` | BLE HID ホスト（Bluedroid + esp_hidh）、ペアリング、自動再接続 |
| `main/input/keyboard.*` | HID レポートからキー入力への変換、キーリピート |
| `main/net/wifi_mgr.*` | Wi-Fi の検索・接続・保存・再接続 |
| `main/net/ssh_client.*` | libssh2 による SSH 接続とデータ転送 |
| `main/storage/*` | NVS の設定、microSD |
| `main/ui/app.*` | メニュー画面とターミナルモード |
| `components/libssh2` | libssh2 を mbedTLS で ESP-IDF 向けにビルドする設定 |

## 使っているもの

- [M5GFX](https://github.com/m5stack/M5GFX)、[M5Unified](https://github.com/m5stack/M5Unified)（MIT）
- [libssh2](https://github.com/libssh2/libssh2) 1.11.1（BSD-3-Clause）
- [ESP-IDF](https://github.com/espressif/esp-idf) 5.5（Apache-2.0）。esp_hid の HID ホストを利用
- 日本語フォント：M5GFX 同梱の efont

このファームウェア自体のライセンスは未設定です。公開するときに決めてください。
