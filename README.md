# NFC出席管理システムのセットアップ手順

## 必要デバイス
- SONY RC-S380
- **Linux系OSのPC**または**DockerのインストールされたPC**
  - 前者を使う場合は手順1-1，後者を使う場合は手順1-2を使用
  - 🚨**注意**：Docker版の場合は音声出力に対応していません

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

## 1-2. Docker版環境構築
### 環境構築
1. ターミナルを開いてこのプロジェクトフォルダに移動

例↓
```sh
cd workSpace/attendance_checker
```
2. Dockerfileからイメージファイルを作成
```sh
docker build -t attendance-app .
```

# 2. Slack Botの追加
1. `20xxgr1_attendance` チャンネルを作成し，メンバーを全員追加
2. このチャンネルのIDをあとで使うのでメモしておく
2. Slackのワークスペースに入っているPCで[Slack apiのサイト]（https://api.slack.com/apps
）を開いて`create new app`を選択
3. `From a scratch`を選択
4. `App Name`は`attendance_announce_bot`等妥当な名前をつける
5. ワークスペースの選択はその年のRM2Cのワークスペースを選択し，Botを作成する
6. 左のメニューから`OAuth & Permissions`を開き，少し下にある`Scopes`の`Bot Token Scopes`に追加で`Chat:write`の権限を与える
7. ページ上部にスクロールしてワークスペースにインストールをクリックしてインストール
8. インストール後，`Bot User OAuth Token`をあとで使うのでメモしておく
9. あとでもう一度このサイトに来るので開いたままにしておく
9. `Installed apps`のBot一覧の中から作成したBotを選択し，Slackで開き，botとのDMチャンネルを開く
10. リーダーとBotとのDMチャンネルのIDをメモしておく
11. 20xxgr1_attendanceチャンネルを開き，`/invite @your-bot-name`コマンドでチャンネルにBotを招待

# 3. Google関連の設定
### Googleスプレッドシートの準備
1. Googleアカウントを用意
2. 出席管理用スプレッドシートを作成（テンプレートをコピー）
3. 作成したスプレッドシートの `sheetID` をあとで使うのでメモしておく（URLの `d/` と `/edit` の間の文字列）

### Google Cloud Platformの設定
1. [Google Cloud Platform](https://console.cloud.google.com/) にアクセス
2. コンソールを開き，新規プロジェクトを作成（名前は自由）
3. 左のメニューから `有効なAPIとサービス` を選択
4. `Google Sheets API` を有効化
5. `Google Drive API` を有効化

### 認証情報の設定
1. `OAuth同意画面` から `開始`
   - アプリ名：自由
   - ユーザーサポートメール：作成したGoogleアカウント
   - 対象：`外部`
   - 連絡先情報：作成したGoogleアカウント
2. 作成を押す
3. `APIとサービス` → `認証情報` → `認証情報を作成`
   - `サービスアカウント` を選択
   - `サービスアカウント名` は自由
   - `ロール` は `オーナー`
   - 完了
4. `サービスアカウントの編集` → `鍵（キー）` → `新しい鍵を作成`
   - `JSON` を選択し，ダウンロード
5. ダウンロードした `JSON` ファイルをプロジェクトフォルダに保存し， `.credential.json` にリネーム
6. `.credential.json` を開き，`client_email` をコピー
7. スプレッドシートを開き，`共有` → `ユーザーを追加` に `client_email` をペーストし，`編集者` に設定
8. 共有リンクを `閲覧者` に設定し， `20xxgr1_attendance` チャンネルにピン留め

### 出席遅刻公欠申請フォーム承認GAS (Google Apps Script)の環境構築
1. Google Formで以下の内容を同じ順番で作成

|項目|タイプ|必須|
|----|----|----|
|学籍番号|短文入力（自由記述）| ✅|
|MTG日程|日付ピッカー（カレンダーから選択）|✅|
|出席/遅刻/公欠|ラジオボタン（単一選択）|✅|
|理由|短文入力（自由記述）| ✅|
|氏名|短文入力（自由記述）|✅| 

2. **Googleフォームの回答先をGoogleスプレッドシートに設定**
（フォーム → 右上の「🔽」 → **「回答先をスプレッドシートにする」**）
3. スプレッドシートのIDを後で使うのでメモしておく
4. スプレッドシート内のメニューにある`拡張機能` ⇨ `Apps Script`を選択
5. GASプロジェクトが作成され，エディタが開くので`form.gs`のスクリプトをコピペ
6. スクリプト内の最初の5つの定数にそれぞれさきほどメモしたIDを記述
```sh
const FORM_SHEET_ID = （申請フォームの回答スプレッドシートのID）
const ATTENDANCE_SHEET_ID = （出席管理スプレッドシートのID）
const SLACK_TOKEN = （Slack Botのトークン）
const APPROVAL_CHANNEL_ID = （グループリーダーのDMチャンネルのID）
const ATTENDANCE_CHANNEL_ID = （20xxgr1_attendanceチャンネルのID）
```
7. エディタの右上にある`デプロイ` ⇨ `New Deploy`を選択
   - タイプ：`Web app`
   - 説明：自由
   - 実行者：自身
   - アクセス権限：誰でも
   - デプロイを選択
8. 下側に表示される`Web app URL`をコピー
9. 先ほど開いていたSlack Botのページを再度開く
10. 左のメニューから`Interactivity & Shortcuts`を選択し，`Interactivity`を有効にする．
11. 先ほどコピーしたURLを`Request URL`に貼り付けて保存
12. GASのページに戻る
13. エディタの左のメニューにあるトリガーを選択
14. 右下のトリガーを追加を選択し，フォームが提出されたとき，`onFormSubmit`関数を実行するようにして保存 

# 4. `.env` ファイルの作成
`.env.example` を参考に，さきほどメモした情報を `.env` に記述
```sh
SHEET_IDv =（スプレッドシートID）
SLACK_BOT_TOKEN = （作成したBotのトークン）
ATTENDANCE_CHANNEL_ID =  （attendanceチャンネルのID）
LATE_TIME_MINUTES = （遅刻判定になる分）
```

# 実行手順
## 5-1. Linux系PC実行手順
1. VS Codeでプロジェクトフォルダを開く
2. ターミナルを開く
3. MTG開始時刻を入力して `attendance.py` を実行
```sh
python3 attendance.py 13:00
```
4. 終了時は `Ctrl + C` で強制終了

## 5-2. Docker実行手順
標準入力にMTG開始時刻を入力してコンテナを起動

例 ↓
```sh
- docker run --rm --device=/dev/bus/usb:/dev/bus/usb attendance-app 13:00
```
終了時は `Ctrl + C` で強制終了