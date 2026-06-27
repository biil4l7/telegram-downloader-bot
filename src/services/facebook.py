import os
import uuid
import logging
import yt_dlp

logger = logging.getLogger(__name__)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "../../downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

FB_EMAIL = os.environ.get("FACEBOOK_EMAIL", "")
FB_PASS = os.environ.get("FACEBOOK_PASSWORD", "")


def download_facebook(url: str) -> str:
    uid = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"fb_{uid}.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    }

    if FB_EMAIL and FB_PASS:
        ydl_opts["username"] = FB_EMAIL
        ydl_opts["password"] = FB_PASS

    logger.info(f"Downloading Facebook: {url}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    base = filename.rsplit(".", 1)[0]
    for ext in ["mp4", "webm", "mkv"]:
        candidate = f"{base}.{ext}"
        if os.path.exists(candidate):
            return candidate

    for f in os.listdir(DOWNLOAD_DIR):
        if uid in f:
            return os.path.join(DOWNLOAD_DIR, f)

    raise FileNotFoundError(f"Facebook file not found for uid {uid}")
