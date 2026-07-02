from .capture import ScreenshotService, capture_region_image, preprocess_image
from .confidence import clamp_confidence, confidence_label
from .engine import MissingOCREngineError, OCREngineError, TesseractOCREngine
from .hauling import HaulingContractsOCRParser
from .parser import OCRParser, ParsedOCRResult
from .profiles import (
    HAULING_CONTRACTS_PROFILE_KEY,
    OCRProfile,
    OCRProfileManager,
    REWARD_SCANNER_PROFILE_KEY,
)
from .regions import OCRRegion
from .reward_scanner import RewardScannerParser, reward_scan_result_from_pipeline
from .results import OCRPipelineResult, OCRResult
from .service import OCRService
from .settings import DEFAULT_OCR_SETTINGS, OCRSettings

__all__ = [
    "DEFAULT_OCR_SETTINGS",
    "HAULING_CONTRACTS_PROFILE_KEY",
    "HaulingContractsOCRParser",
    "MissingOCREngineError",
    "OCREngineError",
    "OCRParser",
    "OCRPipelineResult",
    "OCRProfile",
    "OCRProfileManager",
    "OCRRegion",
    "OCRResult",
    "OCRService",
    "OCRSettings",
    "ParsedOCRResult",
    "REWARD_SCANNER_PROFILE_KEY",
    "RewardScannerParser",
    "ScreenshotService",
    "TesseractOCREngine",
    "capture_region_image",
    "clamp_confidence",
    "confidence_label",
    "preprocess_image",
    "reward_scan_result_from_pipeline",
]
