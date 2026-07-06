from dataclasses import dataclass
from difflib import SequenceMatcher

from .capture import normalize_region
from .reward_scanner import normalize_match_text
from .regions import OCRRegion


BLUEPRINT_REWARD_TRIGGER = "Received Blueprint"
BLUEPRINT_SCAN_INTERVAL_MS = 1000
TRIGGER_TOKEN_MATCH_THRESHOLD = 0.82
TRIGGER_TOKEN_WINDOW = 4
TOAST_GRAY_SATURATION_MAX = 42
TOAST_BRIGHTNESS_MIN = 58
TOAST_BRIGHTNESS_MAX = 225
TOAST_MIN_WIDTH_RATIO = 0.35
TOAST_MIN_HEIGHT_RATIO = 0.06
TOAST_MAX_CENTER_OFFSET_RATIO = 0.32
TOAST_MIN_ASPECT_RATIO = 2.0
TOAST_SCAN_MAX_WIDTH = 640

STATE_IDLE = "Idle"
STATE_TRIGGER_DETECTED = "TriggerDetected"
STATE_SCANNING = "Scanning"
STATE_MATCHED = "Matched"
STATE_WAITING_FOR_WINDOW_CLOSE = "WaitingForWindowClose"


@dataclass(frozen=True)
class ToastDetection:
    detected: bool
    crop_box: tuple[int, int, int, int] | None = None
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self):
        return {
            "detected": self.detected,
            "crop_box": list(self.crop_box) if self.crop_box else None,
            "crop_rect": list(self.crop_box) if self.crop_box else None,
            "confidence": self.confidence,
            "score": self.confidence,
            "reason": self.reason,
        }


def _token_matches(token, expected):
    if token == expected:
        return True
    return SequenceMatcher(None, token, expected).ratio() >= TRIGGER_TOKEN_MATCH_THRESHOLD


def detect_blueprint_reward_trigger(text):
    normalized = normalize_match_text(text)
    if not normalized:
        return False
    if normalize_match_text(BLUEPRINT_REWARD_TRIGGER) in normalized:
        return True

    tokens = normalized.split()
    for index, token in enumerate(tokens):
        if not _token_matches(token, "received"):
            continue
        for candidate in tokens[index + 1:index + 1 + TRIGGER_TOKEN_WINDOW]:
            if _token_matches(candidate, "blueprint"):
                return True
        candidate_tokens = tokens[index + 1:index + 1 + TRIGGER_TOKEN_WINDOW]
        for left, right in zip(candidate_tokens, candidate_tokens[1:]):
            if _token_matches(f"{left}{right}", "blueprint"):
                return True
    return False


def blueprint_name_candidate_present(text):
    lines = [line.strip() for line in str(text or "").splitlines()]
    for index, line in enumerate(lines):
        if not detect_blueprint_reward_trigger(line):
            continue
        if _line_has_name_after_trigger(line):
            return True
        return any(normalize_match_text(candidate) for candidate in lines[index + 1:])
    return False


def _line_has_name_after_trigger(line):
    if ":" in line:
        return bool(normalize_match_text(line.split(":", 1)[1]))

    tokens = normalize_match_text(line).split()
    for index, token in enumerate(tokens):
        if not _token_matches(token, "received"):
            continue
        for candidate_index, candidate in enumerate(tokens[index + 1:], start=index + 1):
            if _token_matches(candidate, "blueprint"):
                return bool(tokens[candidate_index + 1:])
        for left_index in range(index + 1, len(tokens) - 1):
            if _token_matches(f"{tokens[left_index]}{tokens[left_index + 1]}", "blueprint"):
                return bool(tokens[left_index + 2:])
    return False


def detect_notification_toast(image):
    if image is None or not hasattr(image, "convert"):
        return ToastDetection(False, reason="no_image")

    try:
        source_width, source_height = image.size
    except (TypeError, ValueError):
        return ToastDetection(False, reason="invalid_size")
    if source_width <= 0 or source_height <= 0:
        return ToastDetection(False, reason="empty_image")

    working = image.convert("RGB")
    scale = 1.0
    if source_width > TOAST_SCAN_MAX_WIDTH:
        scale = TOAST_SCAN_MAX_WIDTH / source_width
        working = working.resize(
            (TOAST_SCAN_MAX_WIDTH, max(1, int(source_height * scale)))
        )

    width, height = working.size
    pixels = working.load()
    row_counts = [0] * height
    row_min_x = [width] * height
    row_max_x = [-1] * height

    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            brightness = (red + green + blue) / 3
            saturation = max(red, green, blue) - min(red, green, blue)
            if (
                TOAST_BRIGHTNESS_MIN <= brightness <= TOAST_BRIGHTNESS_MAX
                and saturation <= TOAST_GRAY_SATURATION_MAX
            ):
                row_counts[y] += 1
                row_min_x[y] = min(row_min_x[y], x)
                row_max_x[y] = max(row_max_x[y], x)

    row_threshold = max(16, int(width * 0.24))
    runs = []
    start = None
    for index, count in enumerate(row_counts):
        if count >= row_threshold:
            if start is None:
                start = index
        elif start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, height - 1))

    minimum_height = max(18, int(height * TOAST_MIN_HEIGHT_RATIO))
    best = None
    for top, bottom in runs:
        candidate_height = bottom - top + 1
        if candidate_height < minimum_height:
            continue
        min_x = min(row_min_x[top:bottom + 1])
        max_x = max(row_max_x[top:bottom + 1])
        if max_x < min_x:
            continue
        candidate_width = max_x - min_x + 1
        if candidate_width < max(80, int(width * TOAST_MIN_WIDTH_RATIO)):
            continue
        center_offset = abs(((min_x + max_x) / 2) - (width / 2)) / width
        if center_offset > TOAST_MAX_CENTER_OFFSET_RATIO:
            continue
        aspect_ratio = candidate_width / max(1, candidate_height)
        if aspect_ratio < TOAST_MIN_ASPECT_RATIO:
            continue
        density = sum(row_counts[top:bottom + 1]) / max(1, candidate_width * candidate_height)
        score = density + (candidate_width / width) + (candidate_height / height)
        if best is None or score > best[0]:
            best = (score, min_x, top, max_x, bottom, density)

    if not best:
        return ToastDetection(False, reason="toast_shape_not_found")

    _score, min_x, top, max_x, bottom, density = best
    padding = max(4, int(width * 0.01))
    min_x = max(0, min_x - padding)
    top = max(0, top - padding)
    max_x = min(width - 1, max_x + padding)
    bottom = min(height - 1, bottom + padding)
    crop_box = (
        int(min_x / scale),
        int(top / scale),
        min(source_width, int((max_x + 1) / scale)),
        min(source_height, int((bottom + 1) / scale)),
    )
    confidence = min(1.0, max(0.0, density))
    return ToastDetection(True, crop_box=crop_box, confidence=confidence, reason="toast_shape")


def crop_notification_toast(image, detection):
    if not detection or not detection.detected or not detection.crop_box:
        return image
    return image.crop(detection.crop_box)


def title_region_from_reward_region(region, height_ratio=0.28, minimum_height=36):
    region = normalize_region(region)
    trigger_height = max(minimum_height, int(region.height * height_ratio))
    trigger_height = min(region.height, trigger_height)
    return OCRRegion(
        profile=region.profile,
        name=f"{region.name} Trigger",
        x=region.x,
        y=region.y,
        width=region.width,
        height=trigger_height,
        monitor=region.monitor,
        resolution=region.resolution,
        description="Received Blueprint title trigger region.",
    )


@dataclass
class BlueprintRewardWorkflow:
    state: str = STATE_IDLE

    def reset(self):
        self.state = STATE_IDLE

    def visual_toast_seen(self):
        if self.state == STATE_WAITING_FOR_WINDOW_CLOSE:
            return False
        self.state = STATE_TRIGGER_DETECTED
        return True

    def trigger_seen(self, text, visual_toast_detected=False):
        trigger_found = detect_blueprint_reward_trigger(text)
        if self.state == STATE_WAITING_FOR_WINDOW_CLOSE:
            if trigger_found:
                return False
            self.state = STATE_IDLE
            return False

        if not visual_toast_detected:
            return False

        if not trigger_found:
            self.state = STATE_IDLE
            return False

        self.state = STATE_TRIGGER_DETECTED
        return True

    def start_scanning(self):
        self.state = STATE_SCANNING

    def mark_matched(self):
        self.state = STATE_MATCHED

    def wait_for_window_close(self):
        self.state = STATE_WAITING_FOR_WINDOW_CLOSE

    @property
    def waiting_for_window_close(self):
        return self.state == STATE_WAITING_FOR_WINDOW_CLOSE
