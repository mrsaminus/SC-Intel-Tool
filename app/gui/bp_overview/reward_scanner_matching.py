from PySide6.QtGui import QPixmap

from app.ocr.capture import capture_region_image
from app.ocr.reward_scanner import (
    CONFIRM_THRESHOLD,
    STRONG_MATCH_THRESHOLD,
    RewardScannerParser,
    match_blueprint_text,
    normalize_match_text,
    scan_region_for_blueprint_text,
    token_overlap_score,
)


def pixmap_from_image(image):
    from PIL.ImageQt import ImageQt

    qimage = ImageQt(image.convert("RGBA"))
    return QPixmap.fromImage(qimage)


__all__ = [
    "CONFIRM_THRESHOLD",
    "STRONG_MATCH_THRESHOLD",
    "RewardScannerParser",
    "capture_region_image",
    "match_blueprint_text",
    "normalize_match_text",
    "pixmap_from_image",
    "scan_region_for_blueprint_text",
    "token_overlap_score",
]
