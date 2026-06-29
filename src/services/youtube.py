import os
import re
import uuid
import json
import logging
import yt_dlp

logger = logging.getLogger(__name__)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "../../downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Possible cookie file locations (local + Render secret file path)
YT_COOKIE_PATHS = [
    "/etc/secrets/yt_cookies.txt",                                          # Render secret file
    os.path.join(os.path.dirname(__file__), "../../yt_cookies.txt"),        # Local file
    os.path.join(os.path.dirname(__file__), "../../yt_cookies_netscape.txt"),
]

IG_COOKIE_PATHS = [
    "/etc/secrets/ig_cookies.txt",
    os.path.join(os.path.dirname(__file__), "../../ig_cookies_netscape.txt"),
    os.path.join(os.path.dirname(__file__), "../../ig_cookies.txt"),
]


def _find_cookie_file(paths: list) -> str | None:
    for p in paths:
        if os.path.exists(p):
            logger.info(f"Using cookies: {p}")
            return p
    return None


def _base_ydl_opts(extra: dict = {}) -> dict:
    cookies = _find_cookie_file(YT_COOKIE_PATHS)
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {"player_client": ["ios", "android", "web"]}
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        },
        **extra,
    }
    if cookies:
        opts["cookiefile"] = cookies
    return opts


def get_youtube_formats(url: str) -> list[dict]:
    ydl_opts = _base_ydl_opts({"skip_download": True})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    all_formats = info.get("formats", [])
    best_per_height = {}

    for f in all_formats:
        vcodec = f.get("vcodec") or "none"
        height = f.get("height")
        tbr = f.get("tbr") or 0
        fid = f.get("format_id", "")

        if not height or vcodec == "none":
            continue

        prev = best_per_height.get(height)
        if prev is None or tbr > prev["tbr"]:
            best_per_height[height] = {"format_id": fid, "tbr": tbr}

    if not best_per_height:
        return [
            {"label": "🎥 1080p Full HD", "format_id": "bestvideo[height<=1080]", "height": 1080},
            {"label": "🎥 720p HD",       "format_id": "bestvideo[height<=720]",  "height": 720},
            {"label": "🎥 480p",          "format_id": "bestvideo[height<=480]",  "height": 480},
            {"label": "🎥 360p",          "format_id": "bestvideo[height<=360]",  "height": 360},
        ]

    options = []
    for h in sorted(best_per_height.keys(), reverse=True):
        if h >= 2160:   tag = "4K Ultra HD"
        elif h >= 1440: tag = "2K QHD"
        elif h >= 1080: tag = "1080p Full HD"
        elif h >= 720:  tag = "720p HD"
        elif h >= 480:  tag = "480p"
        elif h >= 360:  tag = "360p"
        elif h >= 240:  tag = "240p"
        else:           tag = f"{h}p"
        options.append({
            "label": f"🎥 {tag}",
            "format_id": best_per_height[h]["format_id"],
            "height": h,
        })

    logger.info(f"YT formats found: {[o['label'] for o in options]}")
    return options


def download_youtube(url: str, format_id: str) -> str:
    uid = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"yt_{uid}.%(ext)s")
    is_mp3 = format_id == "mp3_audio"

    if is_mp3:
        ydl_opts = _base_ydl_opts({
            "outtmpl": output_template,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
        })
    else:
        ydl_opts = _base_ydl_opts({
            "outtmpl": output_template,
            "format": f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/best",
            "merge_output_format": "mp4",
        })

    logger.info(f"Downloading YT | format={format_id}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    return _find_file(filename, uid)


def _find_file(filename: str, uid: str) -> str:
    base = os.path.splitext(filename)[0]
    for ext in ["mp4", "mp3", "m4a", "webm", "mkv", "mov"]:
        candidate = f"{base}.{ext}"
        if os.path.exists(candidate):
            return candidate
    for f in sorted(
        os.listdir(DOWNLOAD_DIR),
        key=lambda x: os.path.getmtime(os.path.join(DOWNLOAD_DIR, x)),
        reverse=True,
    ):
        if uid in f:
            return os.path.join(DOWNLOAD_DIR, f)
    raise FileNotFoundError(f"File not found (uid={uid})")