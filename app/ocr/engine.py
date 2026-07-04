import time
from dataclasses import dataclass

from .confidence import clamp_confidence
from .results import OCRResult
from .settings import DEFAULT_OCR_SETTINGS


class OCREngineError(RuntimeError):
    pass


class MissingOCREngineError(OCREngineError):
    pass


@dataclass(frozen=True)
class OCREngineAvailability:
    available: bool
    engine_name: str = ""
    message: str = ""
    status: str = "missing"


class RapidOCREngine:
    name = "RapidOCR"
    _reader = None

    def run(self, image, settings=None):
        _settings = settings or DEFAULT_OCR_SETTINGS
        start = time.perf_counter()
        try:
            numpy, reader = self.load_runtime()
            raw_result, _elapsed = reader(numpy.array(image))
        except MissingOCREngineError:
            raise
        except Exception as exc:
            raise OCREngineError(f"RapidOCR failed: {exc}") from exc

        fragments = normalize_rapidocr_results(raw_result)
        text_lines = reconstruct_ocr_lines(fragments)
        text = "\n".join(text_lines) if text_lines else " ".join(item[1] for item in fragments)
        confidence_values = [item[2] for item in fragments if item[2] is not None]
        confidence = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else None
        )
        return OCRResult(
            text=str(text or ""),
            confidence=clamp_confidence(confidence),
            processing_time=time.perf_counter() - start,
            image_size=getattr(image, "size", None),
            raw_output=fragments,
        )

    @classmethod
    def load_runtime(cls):
        try:
            import numpy
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise MissingOCREngineError(
                "RapidOCR runtime is not installed. Install rapidocr-onnxruntime and numpy."
            ) from exc

        if cls._reader is None:
            cls._reader = RapidOCR()
        return numpy, cls._reader


class TesseractOCREngine:
    name = "Tesseract"

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
            if exc.__class__.__name__ == "TesseractNotFoundError":
                raise MissingOCREngineError(
                    "Tesseract executable was not found. Install Tesseract OCR or use the bundled RapidOCR runtime."
                ) from exc
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
            raise MissingOCREngineError(
                "pytesseract is not installed. Install pytesseract or use the bundled RapidOCR runtime."
            ) from exc

        def run_tesseract(image, settings):
            options = dict(settings.engine_options or {})
            return pytesseract.image_to_string(image, lang=settings.language, **options)

        return run_tesseract


class LocalOCREngine:
    name = "Local OCR"

    def __init__(self, engines=None):
        self.engines = tuple(engines or (RapidOCREngine(), TesseractOCREngine()))
        self.last_engine_name = ""

    def run(self, image, settings=None):
        missing_messages = []
        broken_messages = []
        for engine in self.engines:
            try:
                result = engine.run(image, settings=settings)
                self.last_engine_name = getattr(engine, "name", engine.__class__.__name__)
                return result
            except MissingOCREngineError as exc:
                missing_messages.append(f"{engine.name}: {exc}")
            except OCREngineError as exc:
                broken_messages.append(f"{engine.name}: {exc}")

        if broken_messages:
            details = "; ".join(broken_messages + missing_messages)
            raise OCREngineError(details or "Local OCR engine failed.")

        details = "; ".join(missing_messages)
        raise MissingOCREngineError(details or "No local OCR engine is available.")


def normalize_rapidocr_results(raw_result):
    fragments = []
    for row in raw_result or []:
        if len(row) < 2:
            continue
        bbox = row[0]
        text = str(row[1] or "")
        try:
            confidence = float(row[2]) if len(row) > 2 else None
        except (TypeError, ValueError):
            confidence = None
        if text.strip():
            fragments.append((bbox, text.strip(), confidence))
    return fragments


def reconstruct_ocr_lines(fragments, min_confidence=0.0):
    fragments = [
        fragment for fragment in fragments
        if fragment[2] is None or fragment[2] >= min_confidence
    ]
    if not fragments:
        return []

    def y_center(bbox):
        try:
            ys = [point[1] for point in bbox]
        except (TypeError, IndexError):
            return 0
        return (min(ys) + max(ys)) / 2

    def x_start(bbox):
        try:
            return min(point[0] for point in bbox)
        except (TypeError, IndexError):
            return 0

    def box_height(bbox):
        try:
            ys = [point[1] for point in bbox]
        except (TypeError, IndexError):
            return 12
        return max(1, max(ys) - min(ys))

    sorted_fragments = sorted(fragments, key=lambda item: y_center(item[0]))
    lines = []
    current_line = [sorted_fragments[0]]
    current_y = y_center(sorted_fragments[0][0])

    for fragment in sorted_fragments[1:]:
        fragment_y = y_center(fragment[0])
        threshold = max(box_height(fragment[0]) * 0.6, 8)
        if abs(fragment_y - current_y) <= threshold:
            current_line.append(fragment)
        else:
            lines.append(current_line)
            current_line = [fragment]
            current_y = fragment_y
    lines.append(current_line)

    text_lines = []
    for line in lines:
        line = sorted(line, key=lambda item: x_start(item[0]))
        text_lines.append(" ".join(fragment[1] for fragment in line).strip())
    return [line for line in text_lines if line]


def check_ocr_engine_availability(engine=None):
    engine = engine or LocalOCREngine()
    try:
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (320, 90), "white")
        ImageDraw.Draw(image).text((12, 28), "OCR ready", fill="black")
        result = engine.run(image)
    except MissingOCREngineError as exc:
        return OCREngineAvailability(False, message=str(exc), status="missing")
    except OCREngineError as exc:
        return OCREngineAvailability(False, message=str(exc), status="broken")
    except Exception as exc:
        return OCREngineAvailability(False, message=str(exc), status="broken")

    return OCREngineAvailability(
        True,
        engine_name=getattr(engine, "last_engine_name", "") or getattr(engine, "name", "Local OCR"),
        message=f"OCR engine ready. Test output: {result.text.strip() or 'empty'}",
        status="ready",
    )
