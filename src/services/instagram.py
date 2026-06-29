import os
import uuid
import json
import logging
import yt_dlp

logger = logging.getLogger(__name__)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "../../downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Cookies can come from file OR environment variable
COOKIES_FILE = os.path.join(os.path.dirname(__file__), "../../ig_cookies.txt")
COOKIES_NETSCAPE = os.path.join(os.path.dirname(__file__), "../../ig_cookies_netscape.txt")
IG_COOKIES_ENV = os.environ.get("IG_COOKIES", "").strip()

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


def _write_netscape(cookies: list, path: str):
    lines = ["# Netscape HTTP Cookie File", ""]
    for c in cookies:
        domain = c.get("domain", ".instagram.com")
        if not domain.startswith("."):
            domain = "." + domain
        flag = "TRUE"
        path_ = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expiry = int(c.get("expirationDate", 0))
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append(f"{domain}\t{flag}\t{path_}\t{secure}\t{expiry}\t{name}\t{value}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"Wrote {len(cookies)} cookies to {path}")


def _get_cookies_path() -> str | None:
    # Priority 1: IG_COOKIES environment variable (for Render)
    if IG_COOKIES_ENV:
        try:
            cookies = json.loads(IG_COOKIES_ENV)
            _write_netscape(cookies, COOKIES_NETSCAPE)
            logger.info("Using cookies from IG_COOKIES env var")
            return COOKIES_NETSCAPE
        except Exception as e:
            logger.warning(f"Failed to parse IG_COOKIES env var: {e}")

    # Priority 2: ig_cookies.txt file (for local)
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content.startswith("["):
            try:
                cookies = json.loads(content)
                _write_netscape(cookies, COOKIES_NETSCAPE)
                logger.info("Converted JSON cookies file to Netscape")
                return COOKIES_NETSCAPE
            except Exception as e:
                logger.warning(f"Failed to convert cookies file: {e}")
        else:
            logger.info("Using Netscape cookies file directly")
            return COOKIES_FILE

    logger.warning("No Instagram cookies found — downloads may fail")
    return None


def _base_opts(uid: str, cookies_path: str | None) -> dict:
    opts = {
        "outtmpl": os.path.join(DOWNLOAD_DIR, f"ig_{uid}.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "http_headers": IG_HEADERS,
        "socket_timeout": 30,
        "retries": 3,
    }
    if cookies_path:
        opts["cookiefile"] = cookies_path
    return opts


def download_instagram(url: str) -> str:
    uid = str(uuid.uuid4())[:8]
    cookies_path = _get_cookies_path()
    clean_url = url.split("?")[0].rstrip("/") + "/"

    logger.info(f"Instagram | url={clean_url} | cookies={'yes' if cookies_path else 'no'}")

    for attempt, u in enumerate([clean_url, url, clean_url], 1):
        try:
            opts = _base_opts(uid, cookies_path)
            if attempt == 3:
                opts["format"] = "best"
            return _do_download(opts, u, uid)
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

    base = os.path.splitext(filename)[0]
    for ext in ["mp4", "webm", "mkv", "mov", "m4v"]:
        candidate = f"{base}.{ext}"
        if os.path.exists(candidate):
            return candidate

    for f in sorted(
        os.listdir(DOWNLOAD_DIR),
        key=lambda x: os.path.getmtime(os.path.join(DOWNLOAD_DIR, x)),
        reverse=True
    ):
        if uid in f:
            return os.path.join(DOWNLOAD_DIR, f)

    raise FileNotFoundError(f"Instagram file not found for uid {uid}")