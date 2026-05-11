# ─── Dockerfile ───────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# تثبيت المتطلبات النظامية
RUN apt-get update && apt-get install -y \
    gcc \
    libzmq3-dev \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملفات المتطلبات أولاً للاستفادة من الكاش
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# تشغيل التطبيق
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
