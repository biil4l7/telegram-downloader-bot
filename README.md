# 🎬 Telegram Media Downloader Bot

A powerful Telegram bot that downloads videos from **YouTube, Instagram, TikTok, and Facebook** — with full quality, no watermarks, and smart format selection.

---

## ✨ Features

| Platform | Quality | Notes |
|---|---|---|
| ▶️ YouTube | Up to 4K + MP3 | Interactive quality picker |
| 📸 Instagram | Best available | Reels, posts, stories |
| 🎵 TikTok | Full HD | Watermark-free |
| 📘 Facebook | Best available | Public videos |

- 🎯 **Interactive quality selector** for YouTube (360p → 4K + MP3)
- 🚫 **No watermarks** — TikTok watermark-free via direct API
- 🎵 **MP3 extraction** for audio-only downloads
- ⚡ **Async processing** — no blocking
- 🪵 **Structured logging** with file output
- 🧹 **Auto cleanup** of temp files after sending

---

## 🚀 Quick Start (Local)

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/telegram-downloader-bot.git
cd telegram-downloader-bot
```

### 2. Create your bot
1. Open Telegram → search **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy your **bot token**

### 3. Set up environment
```bash
cp .env.example .env
# Edit .env and paste your BOT_TOKEN
```

### 4. Install dependencies
```bash
# Install ffmpeg (required!)
# macOS:
brew install ffmpeg
# Ubuntu/Debian:
sudo apt install ffmpeg

# Install Python deps
pip install -r requirements.txt
```

### 5. Run
```bash
python src/bot.py
```

---

## ☁️ Deploy on Render.com

### Method 1 — Auto via render.yaml (recommended)

1. Push your code to GitHub (make sure `.env` is in `.gitignore`!)
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your GitHub repo
4. Render detects `render.yaml` automatically
5. In **Environment Variables**, add your `BOT_TOKEN` and any optional credentials
6. Click **Deploy** ✅

### Method 2 — Manual Worker

1. Go to Render → **New** → **Background Worker**
2. Connect your GitHub repo
3. Set:
   - **Build Command:** `apt-get install -y ffmpeg && pip install -r requirements.txt`
   - **Start Command:** `python src/bot.py`
4. Add environment variables (see below)
5. Deploy!

### Environment Variables on Render

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ Yes | Your Telegram bot token |
| `INSTAGRAM_USERNAME` | Optional | For private Instagram content |
| `INSTAGRAM_PASSWORD` | Optional | For private Instagram content |
| `FACEBOOK_EMAIL` | Optional | For private Facebook videos |
| `FACEBOOK_PASSWORD` | Optional | For private Facebook videos |
| `LOG_LEVEL` | Optional | `INFO` (default) |

---

## 📁 Project Structure

```
telegram-downloader-bot/
├── src/
│   ├── bot.py                  # Entry point
│   ├── handlers/
│   │   ├── start.py            # /start and /help commands
│   │   └── downloader.py       # URL handler + quality callback
│   ├── services/
│   │   ├── detector.py         # Platform detection
│   │   ├── youtube.py          # YouTube downloader
│   │   ├── instagram.py        # Instagram downloader
│   │   ├── tiktok.py           # TikTok downloader (no watermark)
│   │   └── facebook.py         # Facebook downloader
│   └── utils/
│       ├── logger.py           # Logging setup
│       └── cleaner.py          # Temp file cleanup
├── downloads/                  # Temp download dir (auto-created)
├── logs/                       # Log files (auto-created)
├── .env                        # Your secrets (never commit!)
├── .env.example                # Template for others
├── .gitignore
├── requirements.txt
├── render.yaml                 # Render.com config
├── Dockerfile                  # Docker support
└── README.md
```

---

## ⚠️ Notes & Limits

- Telegram bots can only send files up to **50MB** — for larger videos, choose a lower quality
- Instagram private content requires account credentials in `.env`
- TikTok watermark removal works for most public videos
- YouTube age-restricted videos may not download without cookies
- Always respect copyright and platform terms of service

---

## 🛠️ Troubleshooting

**Bot doesn't respond?**
→ Check your `BOT_TOKEN` in `.env` or Render environment variables

**"Failed to download" error?**
→ Make sure `ffmpeg` is installed (`ffmpeg -version`)
→ Check if the content is public

**File too large?**
→ Choose a lower resolution for YouTube
→ Render free tier has limited disk — use 480p or lower for free hosting

**TikTok still has watermark?**
→ yt-dlp periodically updates extraction — run `pip install -U yt-dlp`

---

## 📦 Dependencies

- `python-telegram-bot` — Telegram Bot API wrapper
- `yt-dlp` — Universal video downloader
- `ffmpeg` — Video/audio processing (system package)
