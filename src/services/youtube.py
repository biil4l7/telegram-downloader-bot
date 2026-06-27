import os
import re
import uuid
import logging
import yt_dlp

logger = logging.getLogger(__name__)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "../../downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_youtube_formats(url: str) -> list[dict]:
    """
    Fetch ALL video formats and deduplicate by resolution.
    Works with both video-only and video+audio streams.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    all_formats = info.get("formats", [])

    # Collect all formats that have video (any height)
    # key = height, value = best format by tbr
    best_per_height = {}

    for f in all_formats:
        vcodec = f.get("vcodec") or "none"
        height  = f.get("height")
        tbr     = f.get("tbr") or 0
        fid     = f.get("format_id", "")
        ext     = f.get("ext", "mp4")
        acodec  = f.get("acodec") or "none"

        # Must have video
        if not height or vcodec == "none":
            continue

        prev = best_per_height.get(height)
        if prev is None or tbr > prev["tbr"]:
            best_per_height[height] = {
                "format_id": fid,
                "tbr": tbr,
                "ext": ext,
                "height": height,
                "has_audio": acodec != "none",
            }

    if not best_per_height:
        logger.warning("No formats found, using generic fallbacks")
        return [
            {"label": "🎥 1080p FHD", "format_id": "bestvideo[height<=1080]", "height": 1080},
            {"label": "🎥 720p HD",   "format_id": "bestvideo[height<=720]",  "height": 720},
            {"label": "🎥 480p",      "format_id": "bestvideo[height<=480]",  "height": 480},
            {"label": "🎥 360p",      "format_id": "bestvideo[height<=360]",  "height": 360},
        ]

    # Sort heights descending
    sorted_heights = sorted(best_per_height.keys(), reverse=True)

    options = []
    for h in sorted_heights:
        entry = best_per_height[h]

        if h >= 2160:
            tag = "4K Ultra HD"
        elif h >= 1440:
            tag = "2K QHD"
        elif h >= 1080:
            tag = "1080p Full HD"
        elif h >= 720:
            tag = "720p HD"
        elif h >= 480:
            tag = "480p"
        elif h >= 360:
            tag = "360p"
        elif h >= 240:
            tag = "240p"
        else:
            tag = f"{h}p"

        label = f"🎥 {tag}"
        options.append({
            "label": label,
            "format_id": entry["format_id"],
            "height": h,
        })

    logger.info(f"Quality options: {[o['label'] for o in options]}")
    return options


def download_youtube(url: str, format_id: str) -> str:
    uid = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"yt_{uid}.%(ext)s")

    is_mp3 = format_id == "mp3_audio"

    base_opts = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
    }

    if is_mp3:
        ydl_opts = {
            **base_opts,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
        }
    else:
        # Merge chosen video with best audio
        ydl_opts = {
            **base_opts,
            "format": f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/best",
            "merge_output_format": "mp4",
        }

    logger.info(f"Downloading | format={format_id} | url={url}")

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

    raise FileNotFoundError(f"Downloaded file not found (uid={uid})")