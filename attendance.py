import sys
import os
import re
import time
import json
from datetime import datetime, timedelta

import nfc
import gspread
import pygame
import requests
from dotenv import load_dotenv

from google.oauth2.service_account import Credentials

# .envの読み込み
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

# Slack Webhook設定
WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# SEの初期化
pygame.mixer.init()
se_success = pygame.mixer.Sound("scan_success.wav")  # 成功SE
se_error = pygame.mixer.Sound("scan_error.wav")      # エラーSE

if len(sys.argv) < 2:
    print("使用法: python3 attendance.py HH:MM")
    sys.exit(1)

mtg_start_time = datetime.strptime(sys.argv[1], "%H:%M")
late_time = mtg_start_time + timedelta(minutes=10)

def send_slack_notification(message):
    payload = {"text": message}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(WEBHOOK_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Slack通知失敗: {e}")

def ensure_mtg_date():
    today = datetime.now().strftime("%Y-%m-%d")
    records = worksheet.get_all_values()
    if not any(today in row for row in records):
        worksheet.append_row([today, sys.argv[1]])

ensure_mtg_date()
send_slack_notification(f"<!channel>\n出席をとります（MTG開始時刻: {mtg_start_time.strftime('%H:%M')}）")

def on_connect(tag):
    try:
        dump_data = tag.dump()
        student_id = dump_data[13].split('|')[1][2:13].strip()
        hex_data = re.sub(r'[^0-9a-fA-F ]', '', dump_data[14]).strip()
        byte_data = bytes.fromhex(hex_data)
        name = byte_data.decode("shift_jis", errors="ignore").strip()
        
        if not student_id or not name:
            raise ValueError("無効なカード")

        now = datetime.now()
        status = "出席" if now <= late_time else "遅刻"
        worksheet.append_row([student_id, name, now.strftime("%Y-%m-%d %H:%M:%S"), status])
        entry_time = now.strftime("%H:%M:%S")

        if status == "出席":
            send_slack_notification(f"✅ {name} ({student_id}) が出席しました（入室時刻: {entry_time}）")
        else:
            send_slack_notification(f"⚠️ {name} ({student_id}) が遅刻しました（入室時刻: {entry_time}）")

        se_success.play()  # 成功SEを鳴らす

    except Exception as e:
        print(f"無効なカード: {e}")
        se_error.play()  # エラーSEを鳴らす

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
    time.sleep(2) # 2秒おきにカードを読み取る
