from .capture import ScreenshotService, capture_region_image, preprocess_image
from .confidence import clamp_confidence, confidence_label
from .engine import MissingOCREngineError, OCREngineError, TesseractOCREngine
from .parser import OCRParser, ParsedOCRResult
from .regions import OCRRegion
from .reward_scanner import RewardScannerParser, reward_scan_result_from_pipeline
from .results import OCRPipelineResult, OCRResult
from .service import OCRService
from .settings import DEFAULT_OCR_SETTINGS, OCRSettings

__all__ = [
    "DEFAULT_OCR_SETTINGS",
    "MissingOCREngineError",
    "OCREngineError",
    "OCRParser",
    "OCRPipelineResult",
    "OCRRegion",
    "OCRResult",
    "OCRService",
    "OCRSettings",
    "ParsedOCRResult",
    "RewardScannerParser",
    "ScreenshotService",
    "TesseractOCREngine",
    "capture_region_image",
    "clamp_confidence",
    "confidence_label",
    "preprocess_image",
    "reward_scan_result_from_pipeline",
]
