import logging
import os

LOG_DIR = os.path.join(os.path.dirname(__file__), "../../logs")
os.makedirs(LOG_DIR, exist_ok=True)


def setup_logger():
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(LOG_DIR, "bot.log"), encoding="utf-8"),
        ],
    )

    # Silence noisy libraries
    for lib in ["httpx", "telegram", "httpcore"]:
        logging.getLogger(lib).setLevel(logging.WARNING)
