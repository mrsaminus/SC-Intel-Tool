from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OCRResult:
    text: str = ""
    confidence: float | None = None
    processing_time: float = 0.0
    image_size: tuple[int, int] | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    raw_output: Any = None

    @property
    def ok(self):
        return not self.errors


@dataclass(frozen=True)
class OCRPipelineResult:
    status: str
    ocr_result: OCRResult
    parsed_result: Any = None
    message: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self):
        return self.status == "ok" and not self.errors
