# NFC出席管理システムのセットアップ手順

## 必要デバイス
- SONY RC-S380
- **Linux系OSのPC**または**Windows PC (Docker)**
  - 前者を使う場合は手順1-1，後者を使う場合は手順1-2を使用
  - 🚨**注意**：Dockerの場合は音声出力に対応していません．

# 1. 環境構築
## 1-1. Python環境構築
### Homebrewのインストール
```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
次に，PATHを通す（コマンドは人によるけど，調べたらすぐ出てくる）
```sh
brew --version
```
でバージョンが表示されたら成功

### libusbのインストール
```sh
brew install libusb
```

### Pythonのインストール
```sh
brew install python
```

### 必要なPythonライブラリのインストール
```sh
python3 -m pip install --upgrade pip
python3 -m pip install nfcpy gspread pygame requests python-dotenv google-auth
```
- `nfcpy` : NFCの読み取り
- `gspread` : GoogleスプレッドシートAPI
- `pygame` : 音声ファイルの読み込み
- `requests` : HTTPリクエスト
- `python-dotenv` : `.env`ファイルの読み込み
- `google-auth` : Google Cloudサービスへのアクセス

## 1-2. Windows版環境構築
### 必要なもの
NFCリーダをDocker内から使用するため，以下が必要となる．
- `WSL (Windows Subsystem for Linux)`: 説明は割愛
- `Docker Desktop`: 説明は割愛
- `usbipd-win`: 後述

### usbipd-winのインストール
```powershell
winget install --interactive --exact dorssel.usbipd-win
```
### USBデバイスの確認
PowerShellで以下のコマンドを実行し，USBデバイスを確認する．
```powershell
usbipd list
```
以下の例では「BUSID」が「1-2」となっている「NFC Port/PaSoRi 100 USB」がNFCリーダである．
```
> usbipd list
Connected:
BUSID  VID:PID    DEVICE                                                      STATE
1-2    054c:06c3  NFC Port/PaSoRi 100 USB                                       Not shared
1-11   26ce:01a2  USB 入力デバイス                                              Not shared
...
```
### デバイスのバインド・アタッチ
PowerShellで以下のコマンドを実行し，USBデバイスをバインドする．
```powershell
usbipd bind --busid 1-2
```
PowerShellで以下のコマンドを実行し，USBデバイスをアタッチする．
```powershell
usbipd attach --wsl --busid 1-2
```
ここまでで，NFCリーダの「STATE」が「Attached」になっていればよい．
```
> usbipd list
Connected:
BUSID  VID:PID    DEVICE                                                        STATE
1-2    054c:06c3  NFC Port/PaSoRi 100 USB                                       Attached
1-11   26ce:01a2  USB 入力デバイス                                              Not shared
...
```
### WSL側での確認
**WSLのUbuntu**で以下のコマンドを実行し，NFCリーダが認識されることを確認する．
```bash
lsusb
```
以下のような出力が得られる．「Sony Corp. RC-S380」という記載があれば，WSL2側で認識されている．
```
$ lsusb
Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
Bus 001 Device 002: ID 054c:06c3 Sony Corp. RC-S380
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
```

### 環境構築
1. ターミナルを開いてプロジェクトフォルダに移動

例↓
```sh
cd workSpace/attendance_checker
```
2. Dockerfileからイメージファイルを作成
```sh
docker build -t attendance-app .
```

# 2. Slack Botの追加
## Slack Botの作成
1. Slackのワークスペースに入っているブラウザで[Slack APIのサイト](https://api.slack.com/apps)を開く
1. `create new app`を選択
1. `From a scratch`を選択
1. `App Name`は`gr1-attendance-bot`等妥当な名前をつける
1. ワークスペースを選択し，Botを作成する
1. 左のメニューから`OAuth & Permissions`を開き，少し下にある`Scopes`の`Bot Token Scopes`に追加で`Chat:write`の権限を与える
1. ページ上部にスクロールして`Install to your_workspace_name`をクリックしてインストール
1. インストール後，`Bot User OAuth Token`をあとで使うのでメモしておく
### Slack BotとのDMの開放
1. [Slack Marketplace](https://slack.com/marketplace)を開く
1. `Manage`を選択
1. `Instlled apps`内のBot一覧から作成したBotを選択
1. `App Details`を選択
1. `Open in Slack`を選択
1. 作成したSlack BotとのDMチャンネルが開放されるので，この`チャンネルID`をメモしておく
## 学生が出席状況を確認するためのチャンネルの作成
1. チャンネルを作成
   - チャンネル名は自由だが，`gr1-attendance` 等妥当な名前にする
   - このチャンネルの`チャンネルID`をあとで使うのでメモしておく
1. 出席管理対象の学生を全員追加
1. `/invite @your-bot-name`コマンドをチャット欄に打ち込むことでチャンネルにBotを追加

# 3. Google関連の設定
## Googleスプレッドシートの準備
1. Googleアカウントを用意
1. `出席管理シート_template.xlsx`を`Google Drive`にアップロード
1. エクセルファイルを開いた後，`File` > `Save as Google Sheets`を選択し，Google Sheetに変換
1. 変換されたスプレッドシート名を適当な名前に変更する
1. A1セルの説明を参考に，出席管理対象の学籍番号と名前および遅刻判定時間を入力する
   - 他のセルは絶対に触らない
1. 出席管理スプレッドシートの `sheetID` をあとで使うのでメモしておく
   - `sheetID`：URLの `d/` と `/edit` の間の文字列

## Google Cloud Platformの設定
1. [Google Cloud Platform](https://console.cloud.google.com/) にアクセス
2. コンソールを開き，新規プロジェクトを作成（名前は自由）
3. 左のメニューから `有効なAPIとサービス` を選択
4. `Google Sheets API` を有効化
5. `Google Drive API` を有効化

## 認証情報の設定
1. `OAuth同意画面` から `開始`
   - アプリ名：自由
   - ユーザーサポートメール：作成したGoogleアカウントが無難
   - 対象：`外部`
   - 連絡先情報：作成したGoogleアカウントが無難
2. 作成を押す
3. `APIとサービス` → `認証情報` → `認証情報を作成`
   - `サービスアカウント` を選択
   - `サービスアカウント名` は自由
   - `ロール` は `オーナー`
   - 完了
4. `サービスアカウントの編集` → `鍵（キー）` → `新しい鍵を作成`
   - `JSON` を選択し，ダウンロード
5. ダウンロードした `JSON` ファイルをプロジェクトフォルダに保存し， `credentials.json` にリネーム
6. `credentials.json` を開き，`client_email` をコピー
7. スプレッドシートを開き，`共有` → `ユーザーを追加` に `client_email` をペーストし，`編集者` に設定
8. 続いて，共有リンクを `閲覧者` に設定し， 作成したチャンネルで学生にシートを共有およびにピン留め

## 出席遅刻公欠申請フォーム承認GAS (Google Apps Script)の環境構築
### Google Formの作成からGASスクリプト記述まで
1. Google Formで以下の内容を同じ順番で作成

|項目|タイプ|必須回答|
|----|----|----|
|学籍番号|短文入力（自由記述）| ✅|
|MTG日程|日付ピッカー（カレンダーから選択）|✅|
|出席/遅刻/公欠|ラジオボタン（単一選択）|✅|
|理由|短文入力（自由記述）| ✅|
|氏名|短文入力（自由記述）|✅| 
2. **Googleフォームの回答先をGoogleスプレッドシートに設定**
   - `回答` → **「回答先をスプレッドシートにする」**
   - スプレッドシートのIDを後で使うのでメモしておく
1. スプレッドシート内のメニューにある`拡張機能` ⇨ `Apps Script`を選択
   - GASプロジェクトが作成され，エディタが開く
1. `form.gs`のスクリプトをコピペ
1. スクリプト内の最初の5つの定数にそれぞれさきほどメモしたIDを記述
```sh
const FORM_SHEET_ID = （申請フォームの回答スプレッドシートのID）
const ATTENDANCE_SHEET_ID = （出席管理スプレッドシートのID）
const SLACK_TOKEN = （Slack Botのトークン）
const APPROVAL_CHANNEL_ID = （出欠申請承認者のDMチャンネルのID）
const ATTENDANCE_CHANNEL_ID = （出欠を通知するチャンネルのID）
```

### WebデプロイおよびSlack Botとの連携
1. エディタの右上にある`デプロイ` ⇨ `New Deploy`を選択
   - タイプ：`Web app`
   - 説明：自由
   - 実行者：自身
   - アクセス権限：誰でも
   - `デプロイ`を選択
      - この時，警告が出ることがあるが，無視して進んで良い
1. 下側に表示される`Web app URL`をコピー
1. 先ほど開いていた[Slack Botのページ](https://api.slack.com/apps/)を再度開いて，作成したBotを選択
1. 左のメニューから`Interactivity & Shortcuts`を選択し，`Interactivity`を有効にする
1. 先ほどコピーしたURLを`Request URL`に貼り付けて保存

### トリガーの設定
1. GASのページに戻る
1. エディタの左のメニューにあるトリガーを選択
1. 右下のトリガーを追加を選択
   - `Choose which function to run`：`onFormSubmit`
   - `Select event type`：`On form submit`
   - `Save`を選択
      - この時も同様に，警告が出ることがあるが，無視して進んで良い

# 4. `.env` ファイルの作成
1. `.env`ファイルをプロジェクトのルートディレクトリに作成
1. `.env.example` ファイルを参考に，さきほどメモした情報を `.env` ファイルに記述
```sh
ATTENDANCE_SHEET_ID =（スプレッドシートID）
SLACK_BOT_TOKEN = （作成したBotのトークン）
ATTENDANCE_CHANNEL_ID =  （attendanceチャンネルのID）
```

# 実行手順
## 5-1. Linux系PC実行手順
1. ターミナルを開いてプロジェクトフォルダを開く
1. MTG開始時刻を入力して `attendance.py` を実行
```sh
python3 attendance.py 13:00
```
1. 終了時は `Ctrl + C` で強制終了

## 5-2. Docker実行手順
1. 標準入力にMTG開始時刻を入力してコンテナを起動
```sh
docker run --rm --device=/dev/bus/usb:/dev/bus/usb attendance-app 13:00
```
1.終了時は `Ctrl + C` で強制終了
