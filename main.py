if __name__ == "__main__":
    import sys

    from app.logging_config import configure_logging, install_exception_hook

    configure_logging()
    install_exception_hook()

    if "--ocr-self-test" in sys.argv:
        from app.ocr import check_ocr_engine_availability

        availability = check_ocr_engine_availability()
        raise SystemExit(0 if availability.available else 1)

    from app.gui import run_app

    run_app()
