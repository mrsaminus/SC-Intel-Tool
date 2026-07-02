from dataclasses import dataclass, field


@dataclass(frozen=True)
class OCRSettings:
    language: str = "eng"
    preprocessing: bool = True
    grayscale: bool = True
    threshold: int | None = None
    scale: float = 1.0
    invert_colors: bool = False
    engine_options: dict = field(default_factory=dict)

    def normalized_threshold(self):
        if self.threshold is None:
            return None
        return max(0, min(255, int(self.threshold)))

    def normalized_scale(self):
        return max(0.1, float(self.scale or 1.0))

    def to_dict(self):
        return {
            "language": self.language,
            "preprocessing": bool(self.preprocessing),
            "grayscale": bool(self.grayscale),
            "threshold": self.normalized_threshold(),
            "scale": self.normalized_scale(),
            "invert_colors": bool(self.invert_colors),
            "engine_options": dict(self.engine_options or {}),
        }

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        threshold = data.get("threshold")
        if threshold in ("", None):
            threshold = None
        return cls(
            language=str(data.get("language") or "eng"),
            preprocessing=bool(data.get("preprocessing", True)),
            grayscale=bool(data.get("grayscale", True)),
            threshold=threshold,
            scale=data.get("scale", 1.0),
            invert_colors=bool(data.get("invert_colors", False)),
            engine_options=dict(data.get("engine_options") or {}),
        )


DEFAULT_OCR_SETTINGS = OCRSettings()
