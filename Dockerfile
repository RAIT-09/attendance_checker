# 基本となるイメージ
FROM python:3.11-slim

# タイムゾーン設定
ENV TZ=Asia/Tokyo

# 作業ディレクトリの設定
WORKDIR /app

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    libusb-1.0-0-dev \
    libglib2.0-0 \
    libpulse0 \
    && rm -rf /var/lib/apt/lists/*

# アプリケーションのコピー
COPY . /app/
# RUN mv /app/.attendance_docker.py /app/attendance.py

# 必要なPythonライブラリのインストール
RUN pip install --no-cache-dir -r requirements.txt

# 実行コマンドは引数を受け付ける形式に変更
ENTRYPOINT ["python3", "attendance.py"]