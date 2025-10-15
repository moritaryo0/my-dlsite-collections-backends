# Python 3.13のスリムイメージを使用
FROM python:3.13-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY app/ .
COPY manage.py .

# ポート8000を公開
EXPOSE 8000

# Djangoサーバーを起動
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
