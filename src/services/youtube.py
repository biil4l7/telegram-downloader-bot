import os
import uuid
import json
import shutil
import logging
import yt_dlp

logger = logging.getLogger(__name__)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "../../downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YT_COOKIE_PATHS = [
    "/etc/secrets/yt_cookies.txt",
    os.path.join(os.path.dirname(__file__), "../../yt_cookies.txt"),
    os.path.join(os.path.dirname(__file__), "../../yt_cookies_netscape.txt"),
]
TMP_YT_COOKIES = "/tmp/yt_cookies.txt"

# Quality ladder: (height, label, format_string)
QUALITY_LADDER = [
    (2160, "4K Ultra HD",   "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]"),
    (1440, "2K QHD",        "bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best[height<=1440]"),
    (1080, "1080p Full HD", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]"),
    (720,  "720p HD",       "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]"),
    (480,  "480p",          "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]"),
    (360,  "360p",          "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]"),
    (240,  "240p",          "bestvideo[height<=240][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=240]+bestaudio/best[height<=240]"),
]


def _get_yt_cookies() -> str | None:
    for p in YT_COOKIE_PATHS:
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content.startswith("["):
                # JSON — convert to Netscape in /tmp
                cookies = json.loads(content)
                lines = ["# Netscape HTTP Cookie File", ""]
                for c in cookies:
                    domain = c.get("domain", ".youtube.com")
                    if not domain.startswith("."):
                        domain = "." + domain
                    secure = "TRUE" if c.get("secure", False) else "FALSE"
                    expiry = int(c.get("expirationDate", 0))
                    lines.append(f"{domain}\tTRUE\t{c.get('path','/')}\t{secure}\t{expiry}\t{c.get('name','')}\t{c.get('value','')}")
                with open(TMP_YT_COOKIES, "w") as f:
                    f.write("\n".join(lines))
                logger.info(f"Converted JSON cookies from {p}")
                return TMP_YT_COOKIES
            else:
                # Netscape — copy to /tmp
                shutil.copy2(p, TMP_YT_COOKIES)
                logger.info(f"Using cookies from {p}")
                return TMP_YT_COOKIES
        except Exception as e:
            logger.warning(f"Cookie error for {p}: {e}")
    logger.warning("No YouTube cookies found")
    return None


def _ydl_opts(extra: dict = {}) -> dict:
    cookies = _get_yt_cookies()
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
    """
    Probe which quality rungs actually exist for this video,
    using height-based format strings (no raw format IDs).
    """
    probe_opts = _ydl_opts({"skip_download": True})
    with yt_dlp.YoutubeDL(probe_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = info.get("formats", [])
    available_heights = set()
    for f in formats:
        h = f.get("height")
        v = f.get("vcodec", "none")
        if h and v != "none":
            available_heights.add(h)

    logger.info(f"Available heights: {sorted(available_heights, reverse=True)}")

    options = []
    for (rung, label, fmt_str) in QUALITY_LADDER:
        # Include rung if any available height is within range
        if any(rung * 0.85 <= h <= rung * 1.15 or h >= rung for h in available_heights):
            options.append({
                "label": f"🎥 {label}",
                "format_id": fmt_str,   # Store full format string, not raw ID
                "height": rung,
            })

    if not options:
        # Fallback — show all rungs
        options = [
            {"label": f"🎥 {label}", "format_id": fmt_str, "height": rung}
            for rung, label, fmt_str in QUALITY_LADDER
        ]

    logger.info(f"Offering {len(options)} quality options")
    return options


def download_youtube(url: str, format_id: str) -> str:
    """format_id is either 'mp3_audio' or a full yt-dlp format string."""
    uid = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"yt_{uid}.%(ext)s")
    is_mp3 = format_id == "mp3_audio"

    if is_mp3:
        ydl_opts = _ydl_opts({
            "outtmpl": output_template,
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
        })
    else:
        ydl_opts = _ydl_opts({
            "outtmpl": output_template,
            "format": format_id,
            "merge_output_format": "mp4",
        })

    logger.info(f"Downloading YT | format={format_id[:60]}")
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
    raise FileNotFoundError(f"File not found uid={uid}")