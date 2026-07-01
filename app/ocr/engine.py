import time

from .confidence import clamp_confidence
from .results import OCRResult
from .settings import DEFAULT_OCR_SETTINGS


class OCREngineError(RuntimeError):
    pass


class MissingOCREngineError(OCREngineError):
    pass


class TesseractOCREngine:
    def __init__(self, ocr_function=None):
        self.ocr_function = ocr_function

    def run(self, image, settings=None):
        settings = settings or DEFAULT_OCR_SETTINGS
        ocr_function = self.ocr_function or self.default_ocr_function()
        start = time.perf_counter()
        try:
            text = ocr_function(image)
        except MissingOCREngineError:
            raise
        except Exception as exc:
            raise OCREngineError(str(exc)) from exc

        return OCRResult(
            text=str(text or ""),
            confidence=clamp_confidence(None),
            processing_time=time.perf_counter() - start,
            image_size=getattr(image, "size", None),
            raw_output=text,
        )

    def default_ocr_function(self):
        try:
            import pytesseract
        except ImportError as exc:
            raise MissingOCREngineError("No local OCR engine is available.") from exc
        return pytesseract.image_to_string
