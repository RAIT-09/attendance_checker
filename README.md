# NFC出席管理システムのセットアップ手順

## 必要デバイス
- SONY RC-S380
- Linux系OSのPC

## 1. Python環境構築
### Homebrewのインストール
```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
次に，PATHを通す
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

## 2. Slack Botの追加
1. `20xxgr1_attendance` チャンネルを作成し，メンバーを全員追加
2. Slackの `その他` → `自動化` → `App` から `Incoming Webhook` を検索し，`Slackに追加`
3. 投稿先チャンネルとして作成した `20xxgr1_attendance` を選択し，追加
4. 遷移後の画面に表示される `Webhook URL` をあとで使うのでメモしておく

## 3. Google関連の設定
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

## 4. `.env` ファイルの作成
`.env.example` を参考に，さきほどメモした情報を `.env` に記述
```sh
SHEET_ID=（スプレッドシートID）
WEBHOOK_URL=（Webhook URL）
```

## 5. 実行手順
1. VS Codeでプロジェクトフォルダを開く
2. ターミナルを開く
3. MTG開始時刻を入力して `attendance.py` を実行
```sh
python3 attendance.py 13:00
```
4. 終了時は `Ctrl + C` で強制終了