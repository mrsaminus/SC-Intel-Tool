from dataclasses import dataclass, field


@dataclass(frozen=True)
class OCRSettings:
    language: str = "eng"
    grayscale: bool = True
    threshold: int | None = None
    scale: float = 1.0
    engine_options: dict = field(default_factory=dict)

    def normalized_threshold(self):
        if self.threshold is None:
            return None
        return max(0, min(255, int(self.threshold)))

    def normalized_scale(self):
        return max(0.1, float(self.scale or 1.0))


DEFAULT_OCR_SETTINGS = OCRSettings()
