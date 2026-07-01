from app.gui.workers import FunctionWorker


class OCRWorker(FunctionWorker):
    def __init__(self, service, region, parser=None, capture_function=None):
        super().__init__(
            lambda: service.scan_region(
                region,
                parser=parser,
                capture_function=capture_function,
            )
        )


def create_ocr_worker(service, region, parser=None, capture_function=None):
    return OCRWorker(
        service,
        region,
        parser=parser,
        capture_function=capture_function,
    )
