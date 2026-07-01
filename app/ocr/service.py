from .capture import ScreenshotService, normalize_region
from .engine import MissingOCREngineError, OCREngineError, TesseractOCREngine
from .parser import ParsedOCRResult
from .results import OCRPipelineResult, OCRResult
from .settings import DEFAULT_OCR_SETTINGS


class OCRService:
    def __init__(self, screenshot_service=None, engine=None, settings=None):
        self.settings = settings or DEFAULT_OCR_SETTINGS
        self.screenshot_service = screenshot_service or ScreenshotService(settings=self.settings)
        self.engine = engine or TesseractOCREngine()

    def run_ocr(self, image):
        return self.engine.run(image, settings=self.settings)

    def scan_region(self, region, parser=None, capture_function=None):
        region = normalize_region(region)
        try:
            image = capture_function(region) if capture_function else self.screenshot_service.capture_region(region)
        except Exception as exc:
            message = str(exc)
            result = OCRResult(errors=(message,), warnings=("capture_error",))
            return OCRPipelineResult(
                status="capture_error",
                ocr_result=result,
                message=message,
                errors=(message,),
            )

        try:
            result = self.run_ocr(image)
        except MissingOCREngineError as exc:
            message = str(exc)
            result = OCRResult(image_size=getattr(image, "size", None), warnings=("missing_ocr",), errors=(message,))
            return OCRPipelineResult(
                status="missing_ocr",
                ocr_result=result,
                message=message,
                errors=(message,),
            )
        except OCREngineError as exc:
            message = str(exc)
            result = OCRResult(image_size=getattr(image, "size", None), warnings=("ocr_error",), errors=(message,))
            return OCRPipelineResult(
                status="ocr_error",
                ocr_result=result,
                message=message,
                errors=(message,),
            )
        except Exception as exc:
            message = str(exc)
            result = OCRResult(image_size=getattr(image, "size", None), warnings=("ocr_error",), errors=(message,))
            return OCRPipelineResult(
                status="ocr_error",
                ocr_result=result,
                message=message,
                errors=(message,),
            )

        parsed = None
        if parser:
            try:
                parsed = parser.parse(result)
            except Exception as exc:
                message = str(exc)
                parsed = ParsedOCRResult(errors=(message,))
                return OCRPipelineResult(
                    status="parse_error",
                    ocr_result=result,
                    parsed_result=parsed,
                    message=message,
                    errors=(message,),
                )

        return OCRPipelineResult(
            status="ok",
            ocr_result=result,
            parsed_result=parsed,
            warnings=result.warnings,
            errors=result.errors,
        )
