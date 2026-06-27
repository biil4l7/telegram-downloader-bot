import os
import uuid
import logging
import yt_dlp

logger = logging.getLogger(__name__)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "../../downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def download_tiktok(url: str) -> str:
    uid = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"tt_{uid}.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        # Prefer watermark-free format
        "format": "download_addr-0/bestvideo+bestaudio/best",
        "extractor_args": {
            "tiktok": {
                "webpage_download": True,
                # Try to get the no-watermark version
                "api_hostname": "api22-normal-c-useast2a.tiktokv.com",
            }
        },
        "http_headers": {
            "User-Agent": "TikTok/26.2.0 (iPhone; iOS 14.4.2; Scale/3.00)",
        },
    }

    logger.info(f"Downloading TikTok (no watermark): {url}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
    except Exception:
        # Fallback: standard best quality
        ydl_opts_fallback = {
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "format": "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best",
            "merge_output_format": "mp4",
        }
        with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

    base = filename.rsplit(".", 1)[0]
    for ext in ["mp4", "webm"]:
        candidate = f"{base}.{ext}"
        if os.path.exists(candidate):
            return candidate

    for f in os.listdir(DOWNLOAD_DIR):
        if uid in f:
            return os.path.join(DOWNLOAD_DIR, f)

    raise FileNotFoundError(f"TikTok file not found for uid {uid}")
