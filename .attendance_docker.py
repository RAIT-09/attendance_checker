import sys
import os
import re
import time
import json
from datetime import datetime, timedelta

import nfc
from nfc.tag import Tag
from nfc.tag.tt3 import BlockCode, ServiceCode, Type3Tag
from nfc.tag.tt3_sony import FelicaStandard
import gspread
import pygame
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
ATTENDANCE_SHEET_ID = os.getenv("ATTENDANCE_SHEET_ID")
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
CREDENTIALS_FILE = "./credentials.json"

# Google Sheetsの認証
credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
gc = gspread.authorize(credentials)
sh = gc.open_by_key(ATTENDANCE_SHEET_ID)
worksheet = sh.sheet1

# Slack APIを操作するための準備
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
ATTENDANCE_CHANNEL_ID = os.getenv("ATTENDANCE_CHANNEL_ID")
SLACK_API_URL = "https://slack.com/api/chat.postMessage"

# 今日の日付を取得
today = datetime.now().strftime("%-m/%-d")  # "MM/DD" 形式

# MTG開始時刻と遅刻判定時刻を計算
mtg_start_time = datetime.strptime(sys.argv[1], "%H:%M")
records = worksheet.get_all_values()
LATE_TIME_MINUTES = int(records[1][1]) # スプレッドシートのB2セルから遅刻判定時間を取得
late_time = (mtg_start_time + timedelta(minutes=LATE_TIME_MINUTES)).time()

# MTG日時をスプレッドシートに更新
def ensure_mtg_date():
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

# 立命館の学生証を読み取るための定数
SYSTEM_CODE = 0xfe00 # Systemの共通領域
SERVICE_CODE_NUM = 106
SERVICE_ATTRIBUTE = 0x0b # 0x001011（Read Only Access without key）
BLOCK_CODE_NUM_STUDENT_ID = 0
BLOCK_CODE_NUM_STUDENT_NAME = 1

# 指定されたNFCのブロックからshift-jisデコードして中身を返す関数
def read_data_block(tag: Type3Tag, block_code_num: int) -> str:
    service_code = ServiceCode(SERVICE_CODE_NUM, SERVICE_ATTRIBUTE)
    block_code = BlockCode(block_code_num, 0) # '0'は1つだけブロックを読み込む
    read_bytearray = tag.read_without_encryption([service_code], [block_code])
    read_data = read_bytearray.decode("shift_jis")
    return read_data

# 学籍番号を返す関数
def get_student_id(tag: Type3Tag) -> int:
    student_id = read_data_block(tag, BLOCK_CODE_NUM_STUDENT_ID)
    student_id = student_id[2:-3] # スライスで必要な部分だけ切り出す
    return student_id

# 半角ｶﾅ名を返す関数
def get_student_name(tag: Type3Tag) -> str:
    student_name = read_data_block(tag, BLOCK_CODE_NUM_STUDENT_NAME)
    return student_name

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
def on_connect(tag: Tag) -> bool:
    print("connected")
    # カードがFeliCaでかつシステムコードが存在する場合
    if (isinstance(tag, FelicaStandard) 
        and SYSTEM_CODE in tag.request_system_code()):
        tag.idm, tag.pmm, *_ = tag.polling(SYSTEM_CODE)
        student_id = get_student_id(tag)
        student_name = get_student_name(tag)
        records = worksheet.get_all_values()
        student_col = find_student_column(records, student_id)

        if student_col is None:
            print(f"{student_name} ({student_id}) の学籍番号が見つかりませんでした。")
            return True

        if is_already_checked_in(student_col):
            print(f"{student_name} ({student_id}) はすでに出席しています．")
            return True
        
        update_attendance(student_col, student_id, student_name)
    else:
        print(f"無効なカードが読み取られました")

    return True  # Trueを返しておくとタグが存在しなくなるまで待機される

def on_release(tag: Tag) -> None:
    print("released")

while True:
    try:
        with nfc.ContactlessFrontend("usb") as clf:
            try:
                clf.connect(rdwr={"on-connect": on_connect, "on-release": on_release})
            except Exception as e:
                print(f"接続中にエラー: {e}")
    except IOError:
        print("NFCデバイスが見つかりません．1秒後に再試行します．")
        time.sleep(1)