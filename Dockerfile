# ============================================================
#  Dockerfile — Telegram Downloader Bot
# ============================================================

FROM python:3.12-slim

# Install ffmpeg (required for video merging and MP3 conversion)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create directories
RUN mkdir -p downloads logs

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "src/bot.py"]
