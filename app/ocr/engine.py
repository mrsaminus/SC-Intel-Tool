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
        start = time.perf_counter()
        try:
            if self.ocr_function:
                text = self.ocr_function(image)
            else:
                text = self.default_ocr_function()(image, settings)
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

        def run_tesseract(image, settings):
            options = dict(settings.engine_options or {})
            return pytesseract.image_to_string(image, lang=settings.language, **options)

        return run_tesseract
