import difflib
import re

from .capture import capture_region_image
from .engine import TesseractOCREngine
from .parser import OCRParser, ParsedOCRResult
from .regions import OCRRegion
from .service import OCRService


CONFIRM_THRESHOLD = 0.55
STRONG_MATCH_THRESHOLD = 0.75


class RewardScannerParser(OCRParser):
    name = "reward_scanner"

    def __init__(self, blueprints=None, limit=8):
        self.blueprints = tuple(blueprints or ())
        self.limit = limit

    def parse(self, result):
        matches = match_blueprint_text(result.text, self.blueprints, limit=self.limit)
        return ParsedOCRResult(
            data={
                "matches": matches,
                "blueprint_count": len(self.blueprints),
            },
            raw_output=result.text,
        )


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


def scan_region_for_blueprint_text(region, blueprints, capture_function=None, ocr_function=None):
    blueprints = tuple(blueprints or ())
    parser = RewardScannerParser(blueprints)
    engine = TesseractOCREngine(ocr_function=ocr_function)
    service = OCRService(engine=engine)

    def adapted_capture(ocr_region):
        return capture_function(ocr_region.to_tuple())

    pipeline = service.scan_region(
        OCRRegion.from_tuple(region, name="Reward Scanner"),
        parser=parser,
        capture_function=adapted_capture if capture_function else None,
    )

    return reward_scan_result_from_pipeline(pipeline, len(blueprints))


def reward_scan_result_from_pipeline(pipeline, blueprint_count=0):
    if pipeline.status == "capture_error":
        return {
            "status": "capture_error",
            "message": pipeline.message,
            "text": "",
            "matches": [],
            "blueprint_count": blueprint_count,
        }
    if pipeline.status == "missing_ocr":
        return {
            "status": "missing_ocr",
            "message": "",
            "text": "",
            "matches": [],
            "blueprint_count": blueprint_count,
        }
    if pipeline.status in {"ocr_error", "parse_error"}:
        return {
            "status": "ocr_error",
            "message": pipeline.message,
            "text": "",
            "matches": [],
            "blueprint_count": blueprint_count,
        }

    parsed_data = pipeline.parsed_result.data if pipeline.parsed_result else {}
    return {
        "status": "ok",
        "message": "",
        "text": pipeline.ocr_result.text,
        "matches": parsed_data.get("matches", []),
        "blueprint_count": parsed_data.get("blueprint_count", blueprint_count),
    }
