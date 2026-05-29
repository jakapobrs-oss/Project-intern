# Backend image — FastAPI on Python 3.12 slim
FROM python:3.12-slim

# ติดตั้ง system dependency ที่จำเป็น (build tools + libpq สำหรับ asyncpg, ffmpeg สำหรับ transcode)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements ก่อน เพื่อให้ Docker cache layer ของ pip install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose API port
EXPOSE 8000

# Default command (override ใน docker-compose สำหรับ worker)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
