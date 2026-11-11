# PaperDIY Terminal

M5Stack PaperDIY（ESP32-S3、4.7 型 e-paper）を、BLE キーボードで操作する SSH ターミナルにするファームウェアです。PaperDIY PDA Terminal 用に作りました。

> **実機の PaperDIY（Complete Kit）で動いています。** 画面の表示、CACOE キーボードの BLE 接続（自動ペアリング）、Wi-Fi、Raspberry Pi への SSH ログインまで確かめました。ESP-IDF v5.5.6 での再現可能ビルド（同じソースから同じバイナリ）で、ターミナル部分は PC 上でテストしています（vim / less / top / nano / bash / tmux の出力を参照実装 pyte と比較、AddressSanitizer 付き）。長時間の使用、microSD の鍵、tmux などの込み入った画面は、まだ実機で試していません。

目次：[できること](#できること) · [書き込み](#書き込み) · [使い方](#使い方) · [困ったとき](#困ったとき) · [公開鍵認証](#公開鍵認証) · [対応する-ssh-サーバー](#対応する-ssh-サーバー) · [制限と注意](#制限と注意) · [構成](#構成)

## できること

- **BLE キーボード**：HID over GATT のキーボードとペアリングして入力（パスキーは e-paper に表示）。つながっていない間は、ペアリング待ちのキーボードを自分で見つけて接続を始める。次回からはキーを押せば自動で再接続
- **Wi-Fi**：検索して接続、非公開 SSID の手入力、保存済みネットワーク（最大 5 件）への自動接続。ルーターの再起動などで切れても、間隔を空けながらつながるまで再接続
- **SSH**：接続先を最大 8 件保存。パスワード、キーボードインタラクティブ、microSD 上の秘密鍵で認証。ホスト鍵は初回に指紋を確認して保存し、変わったら警告
- **ターミナル**：xterm 互換のサブセット（UTF-8、日本語の全角表示、スクロール領域、代替画面、罫線）。vim、less、top、nano、tmux が動く範囲を想定
- **表示**：24px（80 桁×21 行）と 16px（120 桁×32 行）を切り替え。横長で、USB-C を左にした向き（筐体に入れた向き）が正位置。メニューで上下反転もできる

## 必要なもの

- M5Stack PaperDIY（Assembly Kit / Complete Kit）
- BLE（Bluetooth Low Energy）の HID に対応したキーボード。ESP32-S3 は Bluetooth Classic に対応しないため、Classic 専用のキーボードはつながりません
- ESP-IDF **v5.5.6**（ビルドする場合。別のバージョンでもビルドはできますが、`prebuilt/` と同じバイナリにはなりません）

## 書き込み

### ビルド済みのファームを書く

リポジトリを取ってこなくても、同じファイルが [Releases](https://github.com/tsuyoshi-otake/paperdiy-pda-terminal/releases) の `paperdiy-term-firmware-（版）.zip` に入っています（2 つの bin、`SHA256SUMS`、ビルド条件、ライセンス表示）。その場合は、下のコマンドの `prebuilt/` を、zip を展開したフォルダに読み替えてください。

中身とビルド条件は [`prebuilt/BUILDINFO.md`](prebuilt/BUILDINFO.md)、ファイルが壊れていないかは `sha256sum -c prebuilt/SHA256SUMS` で確かめられます。PaperDIY を USB-C で PC につなぎ、この `firmware/` フォルダで書き込みます。

**初めて書くとき**は、`prebuilt/paperdiy-term-merged.bin`（ブートローダー・パーティション表・本体をまとめたもの）を 0x0 番地に書きます。設定の領域（NVS）も空にするので、前に入っていたファームの設定は消えます。

```bash
python -m esptool --chip esp32s3 -b 460800 write_flash 0x0 prebuilt/paperdiy-term-merged.bin
```

**更新するとき**は、本体だけの `prebuilt/paperdiy-term-app.bin` を 0x20000 番地に書きます。キーボードのペアリング、Wi-Fi、SSH の接続先、ホスト鍵がそのまま残ります（パーティション表を変えた版では、BUILDINFO.md にそう書きます。そのときはまとめた方を書いてください）。

```bash
python -m esptool --chip esp32s3 -b 460800 write_flash 0x20000 prebuilt/paperdiy-term-app.bin
```

Python を入れずに書くなら、Chrome か Edge でブラウザの [ESP Tool](https://espressif.github.io/esptool-js/) を開き、`Connect` で PaperDIY のポート（`USB JTAG/serial debug unit` など）を選んで、同じファイルを同じ番地に書きます（`Flash Address` を 0x0 または 0x20000 に、ファイルを選んで `Program`）。書き込みモードには USB 経由で自動で入ります。

### ソースからビルドする

```bash
git clone --depth 1 --branch v5.5.6 --recursive --shallow-submodules https://github.com/espressif/esp-idf ~/esp/esp-idf-v5.5.6
~/esp/esp-idf-v5.5.6/install.sh esp32s3      # 初回だけ
. ~/esp/esp-idf-v5.5.6/export.sh

cd firmware
./fetch_deps.sh            # M5GFX / M5Unified / libssh2 を固定リビジョンで取得
idf.py build flash monitor # ターゲット（esp32s3）は sdkconfig.defaults で決まっています
```

**再現可能ビルド**：`sdkconfig.defaults` の `CONFIG_APP_REPRODUCIBLE_BUILD=y` で、日時やビルドしたフォルダのパスがバイナリに入らないようにしてあり、バージョンも `version.txt`（0.3.2）で固定しています。ESP-IDF v5.5.6 なら、どこでビルドしても `prebuilt/` と同じバイナリになります（ここで 3 か所と、GitHub Actions のコンテナで確認済み）。リポジトリのルートで

```bash
make firmware          # 上の export.sh を読み込んだシェルで。ビルドして prebuilt/ と 1 バイトずつ比べる
make firmware-docker   # Docker があれば espressif/idf:v5.5.6 のコンテナで同じことをする
```

### ホスト上のテスト

ターミナルエミュレータ（`main/term/vt.cpp`）は PC 上でテストできます。g++ と Python（`pip install -r test/host/requirements.txt`）があれば、リポジトリのルートで `make test` です。決めた手順のエスケープシーケンス（折り返し、全角、罫線、スクロール領域、代替画面、リサイズ、応答）を期待値と比べるテストと、vim / less / top / nano / bash / tmux の実際の出力（`test/host/fixtures/`）を pyte と比べるテストが、AddressSanitizer と UBSan 付きで走ります。

## 使い方

### 1. キーボードをつなぐ（初回）

起動するとキーボードの接続画面になります。

1. キーボードをペアリング（接続待ち）の状態にする。近く（電波の強さ −80 dBm 以上）にあれば、PaperDIY が自分で見つけて接続を始めます
2. 画面に 6 桁の数字が出たら、キーボードでその数字を打って Enter

キーボードがつながっていない間は、いつでもこの自動接続が動いています（登録済みのキーボードがキーを押して戻ってくれば、そちらが優先です）。数字を打たずに失敗したキーボードは 2 分間、メニューで登録を解除したキーボードは 5 分間、自動では選びません。自動で見つからないときや、別のキーボードを選びたいときは、PaperDIY のボタンで一覧から選べます。

1. **ボタンA** で検索
2. 一覧から **ボタンB** で選び、**ボタンA** で接続（一覧の最後の「もう一度検索する / 戻る」で最初の画面に戻れます）
3. 画面に 6 桁の数字が出たら、キーボードでその数字を打って Enter

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

Esc キーのないキーボードでは、キーボードの Fn 層の Esc を使います（CACOE は Fn＋スペース）。SSH 中は Ctrl＋[ でも Esc が送れます。

うまくいかないときは、下の「困ったとき」を見てください。

## 困ったとき

| 症状 | 確かめること |
| --- | --- |
| 画面が上下逆 | USB-C を左にした向きが正位置です。別の向きで使うときは、メニューの設定で上下反転 |
| キーボードがつながらない | キーボードをペアリング状態にし直す（キーボード側に古いペアリング情報が残っていると、明示的にペアリング状態にしないとつながりません）。BLE の HID キーボードか（Bluetooth Classic 専用は不可）。ボタンA で一覧を出して選ぶこともできます |
| 6 桁の数字が出たまま進まない | キーボードで数字を打って Enter。打たずに 30 秒ほどで失敗すると、そのキーボードは 2 分間自動では選びません |
| SSH：「サーバーが TCP の接続を拒否しました（…）」 | 括弧の中の接続先の IP とポートが合っているか。そのポートで sshd が待ち受けているか、ファイアウォールで弾いていないか |
| SSH：「サーバーから応答がありません」「経路がありません」 | 接続先が同じネットワークにあるか（括弧の中にこの端末の IP も出ます）、VPN や Tailscale 経由でないとつながらない相手でないか |
| SSH：「SSH の開始に失敗」 | サーバーの鍵交換・ホスト鍵の方式（下の「対応する SSH サーバー」） |
| SSH：「メモリ不足」 | 0.3.1 で直しました。古い版なら更新してください。出た場合は、エラーに出る空き容量の数字を Issue に書いてください |
| 日本語が化ける | サーバー側のロケールを UTF-8 に（`~/.bashrc` に `export LANG=ja_JP.UTF-8` など）。この端末は接続時に LANG を送りません |
| 書き込んだら設定が消えた | `paperdiy-term-merged.bin` は設定の領域も消します。更新は `paperdiy-term-app.bin` を 0x20000 番地に |

USB でつないでシリアルログ（115200 bps、ESP Tool の `Console` でも読めます）を見ると、起動時と接続の各段階の空きメモリ、つなぎに行った IP、失敗した理由が出ます。

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

- **日本語は表示のみ**で、入力はできません（IME なし）。キー配列は US。日本語入力の対応は [Issue #1](https://github.com/tsuyoshi-otake/paperdiy-pda-terminal/issues/1) で検討しています
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
| `test/host/` | ターミナルエミュレータのホスト上テスト（`make test`） |
| `prebuilt/` | ビルド済みのバイナリ、SHA-256、ビルド条件 |

## 使っているもの

- [M5GFX](https://github.com/m5stack/M5GFX)、[M5Unified](https://github.com/m5stack/M5Unified)（MIT）
- [libssh2](https://github.com/libssh2/libssh2) 1.11.1（BSD-3-Clause）
- [ESP-IDF](https://github.com/espressif/esp-idf) v5.5.6（Apache-2.0）。esp_hid の HID ホストを利用
- 日本語フォント：M5GFX 同梱の efont

このファームウェアのソースコードは [MIT ライセンス](../LICENSE) です。ビルド済みのファーム（`prebuilt/`）に入っているライブラリの著作権表示とライセンス本文は [`prebuilt/THIRD_PARTY_NOTICES.md`](prebuilt/THIRD_PARTY_NOTICES.md) にあります。
