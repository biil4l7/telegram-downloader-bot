from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

WELCOME_MSG = """
🎬 *Welcome to Media Downloader Bot!*

I can download videos and audio from:

▶️ *YouTube* — Video (4K/1080p/720p/480p/360p) + MP3
📸 *Instagram* — Reels, Posts, Stories
🎵 *TikTok* — Videos without watermark
📘 *Facebook* — Public videos

━━━━━━━━━━━━━━━━━━━━━━
*How to use:*
Just send me a link and I'll handle the rest! 🚀

For YouTube, I'll ask you to pick your preferred quality.

━━━━━━━━━━━━━━━━━━━━━━
📌 *Note:* Only public content is supported.
"""

HELP_MSG = """
ℹ️ *Help & FAQ*

*Supported Platforms:*
• 🎬 YouTube — video + MP3 audio
• 📸 Instagram — reels, posts
• 🎵 TikTok — no watermark
• 📘 Facebook — public videos

*How it works:*
1️⃣ Copy the video URL
2️⃣ Paste it here
3️⃣ For YouTube → choose your format/quality
4️⃣ Wait for your download ⬇️

*Tips:*
• Make sure the content is *public*
• Instagram links: use the direct post URL
• Facebook: only public videos work
• Large videos may take a moment

*Problems?* Try sending the link again.
"""

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME_MSG,
        parse_mode=ParseMode.MARKDOWN
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        HELP_MSG,
        parse_mode=ParseMode.MARKDOWN
    )
