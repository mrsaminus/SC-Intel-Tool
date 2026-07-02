from app.gui.workers import FunctionWorker


class OCRWorker(FunctionWorker):
    def __init__(self, service, region, parser=None, capture_function=None, profile=None):
        if profile:
            scan_function = lambda: service.scan_profile_region(
                profile,
                region,
                parser=parser,
                capture_function=capture_function,
            )
        else:
            scan_function = lambda: service.scan_region(
                region,
                parser=parser,
                capture_function=capture_function,
            )
        super().__init__(
            scan_function
        )


def create_ocr_worker(service, region, parser=None, capture_function=None, profile=None):
    return OCRWorker(
        service,
        region,
        parser=parser,
        capture_function=capture_function,
        profile=profile,
    )
