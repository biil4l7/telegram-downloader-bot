import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from services.detector import detect_platform
from services.youtube import get_youtube_formats, download_youtube
from services.instagram import download_instagram
from services.tiktok import download_tiktok
from services.facebook import download_facebook
from utils.cleaner import cleanup_file

logger = logging.getLogger(__name__)

PLATFORM_EMOJIS = {
    "youtube": "▶️",
    "instagram": "📸",
    "tiktok": "🎵",
    "facebook": "📘",
}

IG_ERROR_MSG = (
    "❌ *Instagram download failed.*\n\n"
    "Common reasons:\n"
    "• Content is *private* or requires login\n"
    "• Stories require your credentials in `.env`\n"
    "• Instagram temporarily blocked the request\n\n"
    "💡 For Stories, add to your `.env`:\n"
    "`INSTAGRAM_USERNAME=your@email.com`\n"
    "`INSTAGRAM_PASSWORD=yourpassword`\n\n"
    "Then restart the bot and try again."
)


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    platform = detect_platform(url)

    if not platform:
        await update.message.reply_text(
            "❌ I couldn't recognize that link.\n\n"
            "Supported: YouTube, Instagram, TikTok, Facebook\n"
            "Please send a valid video URL."
        )
        return

    context.user_data["url"] = url
    context.user_data["platform"] = platform
    emoji = PLATFORM_EMOJIS.get(platform, "🎬")

    # ── YouTube: two-step picker ─────────────────────────────────────────
    if platform == "youtube":
        keyboard = [[
            InlineKeyboardButton("🎥  Video", callback_data="yt_type|video"),
            InlineKeyboardButton("🎵  Audio MP3", callback_data="yt_type|audio"),
        ]]
        await update.message.reply_text(
            "▶️ *YouTube link detected!*\n\nChoose what to download:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── All other platforms ──────────────────────────────────────────────
    is_story = platform == "instagram" and "/stories/" in url
    label = "Instagram Story" if is_story else platform.capitalize()
    status_msg = await update.message.reply_text(
        f"{emoji} *Downloading from {label}...*\n⏳ Please wait.",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        file_path = await asyncio.to_thread(_download_by_platform, platform, url)
        await send_file(update, context, file_path, platform, status_msg)
    except Exception as e:
        logger.error(f"{platform} download error: {e}")
        if platform == "instagram":
            await status_msg.edit_text(IG_ERROR_MSG, parse_mode=ParseMode.MARKDOWN)
        else:
            await status_msg.edit_text(
                f"❌ Failed to download from {platform.capitalize()}.\n"
                "Make sure the content is public and try again."
            )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    url = context.user_data.get("url")

    if not url:
        await query.edit_message_text("⚠️ Session expired. Please send the link again.")
        return

    # ── Step 1: Video or Audio ───────────────────────────────────────────
    if data.startswith("yt_type|"):
        chosen = data.split("|", 1)[1]
        context.user_data["yt_type"] = chosen

        if chosen == "audio":
            await query.edit_message_text(
                "🎵 *Downloading MP3...*\n⏳ This may take a moment.",
                parse_mode=ParseMode.MARKDOWN
            )
            try:
                file_path = await asyncio.to_thread(download_youtube, url, "mp3_audio")
                await send_file(update, context, file_path, "youtube", query.message, label="MP3 Audio 320kbps")
            except Exception as e:
                logger.error(f"YouTube MP3 error: {e}")
                err = str(e).lower()
                if "ffmpeg" in err or "postprocessor" in err:
                    await query.edit_message_text(
                        "❌ *MP3 conversion failed.*\n\n"
                        "ffmpeg is not installed or not in PATH.\n\n"
                        "Install it:\n"
                        "• Windows: download from ffmpeg.org, add `bin` folder to PATH\n"
                        "• Mac: `brew install ffmpeg`\n"
                        "• Linux: `sudo apt install ffmpeg`\n\n"
                        "Then restart the bot.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Failed to download audio.\n`{str(e)[:200]}`",
                        parse_mode=ParseMode.MARKDOWN
                    )
            return

        # Video — fetch real available qualities
        await query.edit_message_text(
            "🔍 *Fetching available qualities...*\n⏳ Please wait.",
            parse_mode=ParseMode.MARKDOWN
        )
        try:
            formats = await asyncio.to_thread(get_youtube_formats, url)
            context.user_data["yt_formats"] = formats

            keyboard = []
            for fmt in formats:
                keyboard.append([
                    InlineKeyboardButton(fmt["label"], callback_data=f"yt_dl|{fmt['format_id']}")
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="yt_back")])

            await query.edit_message_text(
                "🎥 *Select video quality:*\n_(only qualities available for this video are shown)_",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"YouTube format fetch error: {e}")
            await query.edit_message_text(
                f"⚠️ Failed to fetch qualities.\n`{str(e)[:200]}`\n\nPlease try again.",
                parse_mode=ParseMode.MARKDOWN
            )
        return

    # ── Back button ──────────────────────────────────────────────────────
    if data == "yt_back":
        keyboard = [[
            InlineKeyboardButton("🎥  Video", callback_data="yt_type|video"),
            InlineKeyboardButton("🎵  Audio MP3", callback_data="yt_type|audio"),
        ]]
        await query.edit_message_text(
            "▶️ *YouTube link detected!*\n\nChoose what to download:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── Step 2: Quality chosen → download ───────────────────────────────
    if data.startswith("yt_dl|"):
        format_id = data.split("|", 1)[1]
        formats = context.user_data.get("yt_formats", [])
        label = next((f["label"].strip() for f in formats if f["format_id"] == format_id), format_id)

        await query.edit_message_text(
            f"⬇️ *Downloading* `{label}`\n⏳ Please wait...",
            parse_mode=ParseMode.MARKDOWN
        )
        try:
            file_path = await asyncio.to_thread(download_youtube, url, format_id)
            await send_file(update, context, file_path, "youtube", query.message, label=label)
        except Exception as e:
            logger.error(f"YouTube download error: {e}")
            err = str(e).lower()
            if "ffmpeg" in err or "merge" in err:
                msg = (
                    "❌ *Download failed — ffmpeg not found.*\n\n"
                    "ffmpeg is required to merge video+audio.\n\n"
                    "Install it:\n"
                    "• Windows: download from ffmpeg.org, add `bin` to PATH\n"
                    "• Mac: `brew install ffmpeg`\n"
                    "• Linux: `sudo apt install ffmpeg`\n\n"
                    "Then restart the bot."
                )
            elif "too large" in err or "filesize" in err:
                msg = "⚠️ File is too large for Telegram (>50MB).\nTry a lower quality."
            else:
                msg = (
                    f"❌ Download failed for `{label}`.\n"
                    "Try a different quality or send the link again."
                )
            await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
        return


def _download_by_platform(platform: str, url: str) -> str:
    if platform == "instagram":
        return download_instagram(url)
    elif platform == "tiktok":
        return download_tiktok(url)
    elif platform == "facebook":
        return download_facebook(url)
    else:
        raise ValueError(f"Unknown platform: {platform}")


async def send_file(
    update, context, file_path: str,
    platform: str, status_msg, label: str = None
):
    emoji = PLATFORM_EMOJIS.get(platform, "🎬")
    caption = f"{emoji} Here's your download"
    if label:
        caption += f"\n📁 `{label.strip()}`"

    try:
        file_size = os.path.getsize(file_path)
        max_size = 50 * 1024 * 1024  # 50 MB Telegram limit

        if file_size > max_size:
            await status_msg.edit_text(
                f"⚠️ File too large for Telegram ({file_size // 1048576}MB > 50MB).\n"
                "Please choose a lower quality."
            )
            cleanup_file(file_path)
            return

        is_audio = file_path.endswith(".mp3") or file_path.endswith(".m4a")

        with open(file_path, "rb") as f:
            if is_audio:
                await update.effective_chat.send_audio(
                    audio=f,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await update.effective_chat.send_video(
                    video=f,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    supports_streaming=True,
                )

        await status_msg.delete()

    except Exception as e:
        logger.error(f"File send error: {e}")
        await status_msg.edit_text("❌ Failed to send the file. Please try again.")
    finally:
        cleanup_file(file_path)