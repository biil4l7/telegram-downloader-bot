FROM python:3.11-slim

# Install ffmpeg and verify it works
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    wget \
    && ffmpeg -version \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

CMD ["python", "src/bot.py"]