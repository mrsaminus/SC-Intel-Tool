from dataclasses import dataclass

from PIL import Image

from app.ocr.capture import ScreenshotService, preprocess_image
from app.ocr.confidence import average_confidence, confidence_label
from app.ocr.engine import MissingOCREngineError, TesseractOCREngine
from app.ocr.parser import OCRParser, ParsedOCRResult
from app.ocr.regions import OCRRegion
from app.ocr.results import OCRResult
from app.ocr.reward_scanner import RewardScannerParser
from app.ocr.service import OCRService
from app.ocr.settings import OCRSettings
from app.ocr.workers import OCRWorker


@dataclass(frozen=True)
class BlueprintStub:
    key: str
    blueprint_name: str


class EchoParser(OCRParser):
    name = "echo"

    def parse(self, result):
        return ParsedOCRResult(data={"text": result.text.upper()})


def test_ocr_region_tuple_and_bbox():
    region = OCRRegion.from_tuple((10, 20, 300, 120), name="Reward")

    assert region.is_valid()
    assert region.to_tuple() == (10, 20, 300, 120)
    assert region.bbox() == (10, 20, 310, 140)


def test_preprocess_image_grayscale_threshold_and_scale():
    image = Image.new("RGB", (10, 5), color=(120, 120, 120))
    processed = preprocess_image(
        image,
        OCRSettings(grayscale=True, threshold=100, scale=2.0),
    )

    assert processed.mode == "L"
    assert processed.size == (20, 10)
    assert processed.getpixel((0, 0)) == 255


def test_tesseract_engine_uses_injected_ocr_function_without_binary():
    image = Image.new("RGB", (2, 2))
    engine = TesseractOCREngine(ocr_function=lambda img: "Local OCR text")

    result = engine.run(image)

    assert result.ok
    assert result.text == "Local OCR text"
    assert result.image_size == (2, 2)
    assert result.processing_time >= 0


def test_ocr_service_runs_capture_engine_and_parser():
    image = Image.new("RGB", (4, 4))
    service = OCRService(engine=TesseractOCREngine(ocr_function=lambda img: "hello"))
    captured = []

    def capture(region):
        captured.append(region.to_tuple())
        return image

    result = service.scan_region((1, 2, 3, 4), parser=EchoParser(), capture_function=capture)

    assert captured == [(1, 2, 3, 4)]
    assert result.status == "ok"
    assert result.ocr_result.text == "hello"
    assert result.parsed_result.data == {"text": "HELLO"}


def test_ocr_service_reports_capture_error():
    service = OCRService(engine=TesseractOCREngine(ocr_function=lambda img: "unused"))

    result = service.scan_region(
        (1, 2, 3, 4),
        capture_function=lambda region: (_ for _ in ()).throw(RuntimeError("screen unavailable")),
    )

    assert result.status == "capture_error"
    assert "screen unavailable" in result.message
    assert result.ocr_result.warnings == ("capture_error",)


def test_ocr_service_reports_missing_engine():
    class MissingEngine:
        def run(self, image, settings=None):
            raise MissingOCREngineError("missing local OCR")

    service = OCRService(engine=MissingEngine())

    result = service.scan_region(
        (1, 2, 3, 4),
        capture_function=lambda region: Image.new("RGB", (2, 2)),
    )

    assert result.status == "missing_ocr"
    assert "missing local OCR" in result.message


def test_reward_scanner_parser_returns_structured_matches():
    parser = RewardScannerParser([BlueprintStub("field-recon-helmet", "Field Recon Helmet")])
    parsed = parser.parse(OCRResult(text="Reward unlocked: Field Recon Helmet"))

    assert parsed.ok
    assert parsed.data["blueprint_count"] == 1
    assert parsed.data["matches"][0]["blueprint"].key == "field-recon-helmet"


def test_ocr_worker_wraps_service_scan():
    service = OCRService(engine=TesseractOCREngine(ocr_function=lambda img: "worker text"))
    worker = OCRWorker(
        service,
        (1, 2, 3, 4),
        parser=EchoParser(),
        capture_function=lambda region: Image.new("RGB", (2, 2)),
    )

    result = worker.function()

    assert result.status == "ok"
    assert result.parsed_result.data == {"text": "WORKER TEXT"}


def test_confidence_helpers():
    assert average_confidence([0.5, 0.75, 2]) == 0.75
    assert confidence_label(0.9) == "High"
    assert confidence_label(None) == "Unknown"
