import difflib
import re

from PySide6.QtGui import QPixmap


CONFIRM_THRESHOLD = 0.55
STRONG_MATCH_THRESHOLD = 0.75


def match_blueprint_text(text, blueprints, limit=8):
    normalized_text = normalize_match_text(text)
    lines = [
        normalize_match_text(line)
        for line in text.splitlines()
        if normalize_match_text(line)
    ]
    matches = []
    for blueprint in blueprints:
        name = blueprint.blueprint_name
        normalized_name = normalize_match_text(name)
        if not normalized_name:
            continue
        if normalized_name in normalized_text:
            confidence = 1.0
            match_type = "exact"
        else:
            line_score = max(
                (difflib.SequenceMatcher(None, normalized_name, line).ratio() for line in lines),
                default=0,
            )
            whole_score = difflib.SequenceMatcher(None, normalized_name, normalized_text).ratio()
            token_score = token_overlap_score(normalized_name, normalized_text)
            confidence = max(line_score, whole_score, token_score)
            match_type = "partial" if confidence >= CONFIRM_THRESHOLD else "none"
        if confidence >= 0.35:
            matches.append({
                "blueprint": blueprint,
                "confidence": confidence,
                "match_type": match_type,
                "name_length": len(normalized_name),
            })

    matches.sort(key=lambda item: (
        -item["confidence"],
        -item["name_length"],
        item["blueprint"].blueprint_name.lower(),
    ))
    return matches[:limit]


def normalize_match_text(text):
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def token_overlap_score(name, text):
    name_tokens = set(name.split())
    text_tokens = set(text.split())
    if not name_tokens:
        return 0
    overlap = len(name_tokens & text_tokens) / len(name_tokens)
    if overlap < 0.5:
        return overlap * 0.5
    return min(0.85, overlap)


def capture_region_image(region):
    from PIL import ImageGrab

    x, y, width, height = region
    return ImageGrab.grab(bbox=(x, y, x + width, y + height))


def pixmap_from_image(image):
    from PIL.ImageQt import ImageQt

    qimage = ImageQt(image.convert("RGBA"))
    return QPixmap.fromImage(qimage)
