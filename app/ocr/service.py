from .capture import ScreenshotService, normalize_region, preprocess_image
from .engine import LocalOCREngine, MissingOCREngineError, OCREngineError
from .parser import ParsedOCRResult
from .profiles import normalize_profile
from .results import OCRPipelineResult, OCRResult
from .settings import DEFAULT_OCR_SETTINGS


class OCRService:
    def __init__(self, screenshot_service=None, engine=None, settings=None):
        self.settings = settings or DEFAULT_OCR_SETTINGS
        self.screenshot_service = screenshot_service or ScreenshotService(settings=self.settings)
        self.engine = engine or LocalOCREngine()

    def run_ocr(self, image, settings=None):
        return self.engine.run(image, settings=settings or self.settings)

    def scan_image(self, image, parser=None, settings=None, preprocess=True):
        settings = settings or self.settings
        image_error = self.image_validation_error(image)
        if image_error:
            result = OCRResult(errors=(image_error,), warnings=("capture_error",))
            return OCRPipelineResult(
                status="capture_error",
                ocr_result=result,
                message=image_error,
                errors=(image_error,),
                captured_image=image,
            )

        ocr_image = preprocess_image(image, settings=settings) if preprocess else image
        try:
            result = self.run_ocr(ocr_image, settings=settings)
        except MissingOCREngineError as exc:
            message = str(exc)
            result = OCRResult(image_size=getattr(ocr_image, "size", None), warnings=("missing_ocr",), errors=(message,))
            return OCRPipelineResult(
                status="missing_ocr",
                ocr_result=result,
                message=message,
                errors=(message,),
                captured_image=image,
            )
        except OCREngineError as exc:
            message = str(exc)
            result = OCRResult(image_size=getattr(ocr_image, "size", None), warnings=("ocr_error",), errors=(message,))
            return OCRPipelineResult(
                status="ocr_error",
                ocr_result=result,
                message=message,
                errors=(message,),
                captured_image=image,
            )
        except Exception as exc:
            message = str(exc)
            result = OCRResult(image_size=getattr(ocr_image, "size", None), warnings=("ocr_error",), errors=(message,))
            return OCRPipelineResult(
                status="ocr_error",
                ocr_result=result,
                message=message,
                errors=(message,),
                captured_image=image,
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
                    captured_image=image,
                )

        return OCRPipelineResult(
            status="ok",
            ocr_result=result,
            parsed_result=parsed,
            warnings=result.warnings,
            errors=result.errors,
            captured_image=image,
        )

    def scan_region(self, region, parser=None, capture_function=None, settings=None):
        settings = settings or self.settings
        region = normalize_region(region)
        try:
            image = (
                capture_function(region)
                if capture_function
                else self.screenshot_service.capture_region(region, settings=settings)
            )
        except Exception as exc:
            message = str(exc)
            result = OCRResult(errors=(message,), warnings=("capture_error",))
            return OCRPipelineResult(
                status="capture_error",
                ocr_result=result,
                message=message,
                errors=(message,),
            )

        image_error = self.image_validation_error(image)
        if image_error:
            result = OCRResult(errors=(image_error,), warnings=("capture_error",))
            return OCRPipelineResult(
                status="capture_error",
                ocr_result=result,
                message=image_error,
                errors=(image_error,),
                captured_image=image,
            )

        return self.scan_image(image, parser=parser, settings=settings, preprocess=False)

    def scan_profile_region(self, profile, region, parser=None, capture_function=None):
        profile = normalize_profile(profile)
        region = normalize_region(region)
        if not region.profile:
            region = type(region)(
                profile=profile.key,
                name=region.name,
                x=region.x,
                y=region.y,
                width=region.width,
                height=region.height,
                monitor=region.monitor,
                resolution=region.resolution,
                description=region.description,
            )
        return self.scan_region(
            region,
            parser=parser,
            capture_function=capture_function,
            settings=profile.to_settings(),
        )

    @staticmethod
    def image_validation_error(image):
        if image is None:
            return "No image was captured."
        size = getattr(image, "size", None)
        if size:
            try:
                width, height = size
            except (TypeError, ValueError):
                return ""
            if width <= 0 or height <= 0:
                return "Captured image is empty."
        return ""
