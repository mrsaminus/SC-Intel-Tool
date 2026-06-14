if __name__ == "__main__":
    from app.logging_config import configure_logging, install_exception_hook

    configure_logging()
    install_exception_hook()

    from app.gui import run_app

    run_app()
