from dataclasses import dataclass


@dataclass(frozen=True)
class OCRRegion:
    name: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    resolution: str = ""
    description: str = ""

    @classmethod
    def from_tuple(cls, region, name="", description="", resolution=""):
        x, y, width, height = region
        return cls(
            name=name,
            x=int(x),
            y=int(y),
            width=int(width),
            height=int(height),
            resolution=resolution,
            description=description,
        )

    def to_tuple(self):
        return self.x, self.y, self.width, self.height

    def bbox(self):
        return self.x, self.y, self.x + self.width, self.y + self.height

    def is_valid(self):
        return self.width > 0 and self.height > 0
