import os
import logging

logger = logging.getLogger(__name__)


def cleanup_file(file_path: str):
    """Safely delete a downloaded file after sending."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Cleaned up: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to clean up {file_path}: {e}")
