from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedOCRResult:
    data: Any = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    raw_output: Any = None

    @property
    def ok(self):
        return not self.errors


class OCRParser:
    name = "base"

    def parse(self, result):
        raise NotImplementedError
