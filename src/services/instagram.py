import os
import uuid
import json
import shutil
import logging
import yt_dlp

logger = logging.getLogger(__name__)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "../../downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

IG_COOKIE_PATHS = [
    "/etc/secrets/ig_cookies.txt",
    os.path.join(os.path.dirname(__file__), "../../ig_cookies_netscape.txt"),
    os.path.join(os.path.dirname(__file__), "../../ig_cookies.txt"),
]

COOKIES_NETSCAPE = os.path.join(os.path.dirname(__file__), "../../ig_cookies_netscape.txt")

IG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.instagram.com/",
    "Origin": "https://www.instagram.com",
}

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
logger.info(f"ffmpeg available: {FFMPEG_AVAILABLE}")

if FFMPEG_AVAILABLE:
    FORMAT_PRIMARY  = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    FORMAT_FALLBACK = "best[ext=mp4]/best"
else:
    FORMAT_PRIMARY  = "best[vcodec!=none][acodec!=none][ext=mp4]/best[vcodec!=none][acodec!=none]/best[ext=mp4]/best"
    FORMAT_FALLBACK = "best"


def _write_netscape(cookies: list, path: str):
    lines = ["# Netscape HTTP Cookie File", ""]
    for c in cookies:
        domain = c.get("domain", ".instagram.com")
        if not domain.startswith("."):
            domain = "." + domain
        path_ = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expiry = int(c.get("expirationDate", 0))
        name   = c.get("name", "")
        value  = c.get("value", "")
        lines.append(f"{domain}\tTRUE\t{path_}\t{secure}\t{expiry}\t{name}\t{value}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _get_cookies_path() -> str | None:
    for p in IG_COOKIE_PATHS:
        if not os.path.exists(p):
            continue
        with open(p, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content.startswith("["):
            try:
                cookies = json.loads(content)
                _write_netscape(cookies, COOKIES_NETSCAPE)
                logger.info(f"Converted JSON cookies from {p}")
                return COOKIES_NETSCAPE
            except Exception as e:
                logger.warning(f"Failed to convert {p}: {e}")
        else:
            logger.info(f"Using cookies: {p}")
            return p
    logger.warning("No Instagram cookies found")
    return None


def _base_opts(uid: str, cookies_path: str | None, fmt: str) -> dict:
    opts = {
        "outtmpl": os.path.join(DOWNLOAD_DIR, f"ig_{uid}.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "format": fmt,
        "http_headers": IG_HEADERS,
        "socket_timeout": 30,
        "retries": 3,
    }
    if FFMPEG_AVAILABLE:
        opts["merge_output_format"] = "mp4"
    if cookies_path:
        opts["cookiefile"] = cookies_path

    # ── DEBUG LINE — remove after confirming audio works ──
    logger.info(f"IG ydl_opts format: {opts['format']} | ffmpeg: {FFMPEG_AVAILABLE}")

    return opts


def download_instagram(url: str) -> str:
    uid = str(uuid.uuid4())[:8]
    cookies_path = _get_cookies_path()
    clean_url = url.split("?")[0].rstrip("/") + "/"

    logger.info(
        f"Instagram | url={clean_url} | "
        f"cookies={'yes' if cookies_path else 'no'} | "
        f"ffmpeg={FFMPEG_AVAILABLE}"
    )

    attempts = [
        (clean_url, FORMAT_PRIMARY),
        (url,       FORMAT_PRIMARY),
        (clean_url, FORMAT_FALLBACK),
    ]

    for attempt, (u, fmt) in enumerate(attempts, 1):
        try:
            opts = _base_opts(uid, cookies_path, fmt)
            result = _do_download(opts, u, uid)
            logger.info(f"Instagram success on attempt {attempt} | file={result}")
            return result
        except Exception as e:
            logger.warning(f"IG attempt {attempt} failed: {e}")

    raise Exception("instagram_failed")


def _do_download(ydl_opts: dict, url: str, uid: str) -> str:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info.get("_type") == "playlist":
            entries = info.get("entries", [])
            if entries:
                info = entries[0]
        filename = ydl.prepare_filename(info)

    # ── DEBUG: log what yt-dlp actually selected ──
    logger.info(f"IG downloaded file: {filename}")

    base = os.path.splitext(filename)[0]
    for ext in ["mp4", "webm", "mkv", "mov", "m4v"]:
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

    raise FileNotFoundError(f"Instagram file not found uid={uid}")
