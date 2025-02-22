import sys
import os
import re
import time
import json
from datetime import datetime, timedelta

import nfc
import gspread
import requests
from dotenv import load_dotenv

from google.oauth2.service_account import Credentials

# 実行方法間違えたら最初に教えて終了
if len(sys.argv) < 2:
    print("使用法: python3 attendance.py HH:MM")
    sys.exit(1)

# .envファイルの読み込み
load_dotenv()

# Google Sheets API 認証設定
SHEET_ID = os.getenv("SHEET_ID")
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
CREDENTIALS_FILE = "./.credentials.json"

# Google Sheetsの認証
credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
gc = gspread.authorize(credentials)
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.sheet1

# Slack APIを操作するための準備
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
ATTENDANCE_CHANNEL_ID = os.getenv("ATTENDANCE_CHANNEL_ID")
SLACK_API_URL = "https://slack.com/api/chat.postMessage"

# 今日の日付を取得
today = datetime.now().strftime("%-m/%-d")  # "MM/DD" 形式

# MTG開始時刻と遅刻判定時刻を計算
mtg_start_time = datetime.strptime(sys.argv[1], "%H:%M")
LATE_TIME_MINUTES = int(os.getenv("LATE_TIME_MINUTES", 10))
late_time = (mtg_start_time + timedelta(minutes=LATE_TIME_MINUTES)).time()

# MTG日時をスプレッドシートに更新
def ensure_mtg_date():
    records = worksheet.get_all_values()

    for i, row in enumerate(records[3:], start=4):
        if row[0] == today:
            worksheet.update_cell(i, 2, sys.argv[1])  # 時刻を更新
            return i  # 更新した行番号を返す

    new_row_index = len(records) + 1
    worksheet.insert_row([today, sys.argv[1]], new_row_index, value_input_option="USER_ENTERED")
    return new_row_index

mtg_row_to_update = ensure_mtg_date()

# 文字列を受け取ってSlackにメッセージを送信する関数
def send_slack_notification(message):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
    }
    payload = {
        "channel": ATTENDANCE_CHANNEL_ID,
        "text": message
    }
    
    try:
        response = requests.post(SLACK_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Slack通知失敗: {e}")

send_slack_notification(f"<!channel>\n出席をとります（MTG開始時刻: {mtg_start_time.strftime('%H:%M')}）")

# 学生証のデータを抽出
def extract_card_data(tag):
    dump_data = tag.dump()
    student_id = dump_data[13].split('|')[1][2:13].strip()
    hex_data = re.sub(r'[^0-9a-fA-F ]', '', dump_data[14]).strip()
    byte_data = bytes.fromhex(hex_data)
    name = byte_data.decode("shift_jis", errors="ignore").strip()

    if not student_id or not name:
        raise ValueError("無効なカード")

    return student_id, name

# 学生の学籍番号に対応する列を検索
def find_student_column(records, student_id):
    header_row = records[2]
    for col_num, header in enumerate(header_row):
        if header == student_id:
            return col_num + 1  # 学籍番号が一致する列（1-based index）
    return None

# すでに出席済みかを確認
def is_already_checked_in(student_col):
    if worksheet.cell(mtg_row_to_update, student_col).value:
        return True
    return False    

# 出席情報を更新
def update_attendance(student_col, student_id, name):
    now = datetime.now().time()
    entry_time = now.strftime("%H:%M:%S")
    status = "出席" if now <= late_time else "遅刻"

    worksheet.update_cell(mtg_row_to_update, student_col, entry_time)

    if status == "出席":
        send_slack_notification(f"✅ {name} ({student_id}) が出席しました（入室時刻: {entry_time}）")
    else:
        send_slack_notification(f"⚠️ {name} ({student_id}) が遅刻しました（入室時刻: {entry_time}）")

# NFCタグが接続された際に呼ばれる関数
def on_connect(tag):
    try:
        student_id, name = extract_card_data(tag)
        
        records = worksheet.get_all_values()
        student_col = find_student_column(records, student_id)

        if student_col is None:
            print(f"{name} ({student_id}) の学籍番号が見つかりませんでした。")
            return

        if is_already_checked_in(student_col):
            print(f"{name} ({student_id}) はすでに出席しています．")
            return
        
        update_attendance(student_col, student_id, name)

    except Exception as e:
        print(f"無効なカード: {e}")\

while True:
    try:
        clf = nfc.ContactlessFrontend('usb')
        clf.connect(rdwr={'on-connect': on_connect})
    except IOError as e:
        print(f"接続に失敗しました: {e}")
        time.sleep(1)
        continue
    finally:
        clf.close()
    time.sleep(2)  # 2秒おきにカードを読み取る