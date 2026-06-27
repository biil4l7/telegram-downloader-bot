import re

PATTERNS = {
    "youtube": [
        r"(https?://)?(www\.)?(youtube\.com/watch|youtu\.be/|youtube\.com/shorts/|youtube\.com/live/)",
        r"(https?://)?(www\.)?youtube\.com/.*[?&]v=",
    ],
    "instagram": [
        r"(https?://)?(www\.)?instagram\.com/(p|reel|tv|stories)/",
    ],
    "tiktok": [
        r"(https?://)?(www\.|vm\.)?tiktok\.com/",
    ],
    "facebook": [
        r"(https?://)?(www\.|m\.|web\.)?facebook\.com/.*(video|watch|reel)",
        r"(https?://)?fb\.watch/",
        r"(https?://)?(www\.)?facebook\.com/share/",
    ],
}

def detect_platform(url: str) -> str | None:
    for platform, patterns in PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return platform
    return None
