from dataclasses import dataclass


@dataclass(frozen=True)
class OCRRegion:
    profile: str = ""
    name: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    monitor: int | None = None
    resolution: str = ""
    description: str = ""

    @classmethod
    def from_tuple(cls, region, name="", description="", resolution="", profile="", monitor=None):
        x, y, width, height = region
        return cls(
            profile=profile,
            name=name,
            x=int(x),
            y=int(y),
            width=int(width),
            height=int(height),
            monitor=monitor,
            resolution=resolution,
            description=description,
        )

    def to_tuple(self):
        return self.x, self.y, self.width, self.height

    def bbox(self):
        return self.x, self.y, self.x + self.width, self.y + self.height

    def is_valid(self):
        return self.width > 0 and self.height > 0

    def to_dict(self):
        return {
            "profile": self.profile,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "monitor": self.monitor,
            "resolution": self.resolution,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        monitor = data.get("monitor")
        if monitor == "":
            monitor = None
        return cls(
            profile=str(data.get("profile") or ""),
            name=str(data.get("name") or ""),
            x=int(data.get("x") or 0),
            y=int(data.get("y") or 0),
            width=int(data.get("width") or 0),
            height=int(data.get("height") or 0),
            monitor=monitor,
            resolution=str(data.get("resolution") or ""),
            description=str(data.get("description") or ""),
        )
