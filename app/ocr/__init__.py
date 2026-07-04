from .capture import ScreenshotService, capture_region_image, preprocess_image
from .blueprint_reward_workflow import (
    BLUEPRINT_REWARD_TRIGGER,
    BlueprintRewardWorkflow,
    detect_blueprint_reward_trigger,
    title_region_from_reward_region,
)
from .confidence import clamp_confidence, confidence_label
from .debug_capture import (
    OCR_DEBUG_ENABLED_SETTING_KEY,
    clear_ocr_debug_captures,
    format_debug_size,
    get_ocr_debug_root,
    get_ocr_debug_summary,
    is_ocr_debug_enabled,
    set_ocr_debug_enabled,
    start_ocr_debug_session,
)
from .engine import (
    LocalOCREngine,
    MissingOCREngineError,
    OCREngineAvailability,
    OCREngineError,
    RapidOCREngine,
    TesseractOCREngine,
    check_ocr_engine_availability,
)
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
    "BLUEPRINT_REWARD_TRIGGER",
    "BlueprintRewardWorkflow",
    "HAULING_CONTRACTS_PROFILE_KEY",
    "HaulingContractsOCRParser",
    "LocalOCREngine",
    "MissingOCREngineError",
    "OCREngineAvailability",
    "OCREngineError",
    "OCRParser",
    "OCRPipelineResult",
    "OCR_DEBUG_ENABLED_SETTING_KEY",
    "OCRProfile",
    "OCRProfileManager",
    "OCRRegion",
    "OCRResult",
    "OCRService",
    "OCRSettings",
    "ParsedOCRResult",
    "REWARD_SCANNER_PROFILE_KEY",
    "RapidOCREngine",
    "RewardScannerParser",
    "ScreenshotService",
    "TesseractOCREngine",
    "capture_region_image",
    "check_ocr_engine_availability",
    "clear_ocr_debug_captures",
    "clamp_confidence",
    "confidence_label",
    "detect_blueprint_reward_trigger",
    "format_debug_size",
    "get_ocr_debug_root",
    "get_ocr_debug_summary",
    "is_ocr_debug_enabled",
    "preprocess_image",
    "reward_scan_result_from_pipeline",
    "set_ocr_debug_enabled",
    "start_ocr_debug_session",
    "title_region_from_reward_region",
]
