from .regions import OCRRegion
from .settings import DEFAULT_OCR_SETTINGS


class ScreenshotService:
    def __init__(self, settings=None):
        self.settings = settings or DEFAULT_OCR_SETTINGS

    def capture_region(self, region, preprocess=True, settings=None):
        from PIL import ImageGrab

        region = normalize_region(region)
        if not region.is_valid():
            raise ValueError("OCR region must have positive width and height.")
        image = ImageGrab.grab(bbox=region.bbox())
        if preprocess:
            return preprocess_image(image, settings or self.settings)
        return image

    def capture_full_monitor(self, preprocess=True, settings=None):
        from PIL import ImageGrab

        image = ImageGrab.grab()
        if preprocess:
            return preprocess_image(image, settings or self.settings)
        return image

    def capture_active_window(self, *_args, **_kwargs):
        raise NotImplementedError("Active-window OCR capture is not implemented yet.")


def normalize_region(region):
    if isinstance(region, OCRRegion):
        return region
    return OCRRegion.from_tuple(region)


def preprocess_image(image, settings=None):
    settings = settings or DEFAULT_OCR_SETTINGS
    processed = image
    if not settings.preprocessing:
        return processed
    if settings.grayscale:
        processed = processed.convert("L")

    if settings.invert_colors:
        from PIL import ImageOps

        if processed.mode not in {"L", "RGB"}:
            processed = processed.convert("RGB")
        processed = ImageOps.invert(processed)

    threshold = settings.normalized_threshold()
    if threshold is not None:
        if processed.mode != "L":
            processed = processed.convert("L")
        processed = processed.point(lambda pixel: 255 if pixel >= threshold else 0)

    scale = settings.normalized_scale()
    if scale != 1.0:
        width, height = processed.size
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        processed = processed.resize(new_size)

    return processed


def capture_region_image(region, settings=None):
    return ScreenshotService(settings=settings).capture_region(region)
