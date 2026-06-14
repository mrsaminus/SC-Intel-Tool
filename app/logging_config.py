import logging
import sys
from logging.handlers import RotatingFileHandler

from .paths import get_user_data_dir


LOG_FILE_NAME = "sc_intel_tool.log"
_CONFIGURED = False
_HOOK_INSTALLED = False


def get_log_file_path():
    log_dir = get_user_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / LOG_FILE_NAME


def _existing_sc_intel_handler(root_logger):
    for handler in root_logger.handlers:
        if getattr(handler, "_sc_intel_tool_handler", False):
            return handler
    return None


def configure_logging():
    global _CONFIGURED
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    existing_handler = _existing_sc_intel_handler(root)
    if existing_handler:
        _CONFIGURED = True
        return get_log_file_path()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        log_path = get_log_file_path()
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        file_handler._sc_intel_tool_handler = True
        root.addHandler(file_handler)
    except OSError as exc:
        log_path = None
        fallback_handler = logging.StreamHandler()
        fallback_handler.setFormatter(formatter)
        fallback_handler.setLevel(logging.INFO)
        fallback_handler._sc_intel_tool_handler = True
        root.addHandler(fallback_handler)
        logging.getLogger(__name__).warning("File logging unavailable: %s", exc)

    _CONFIGURED = True
    logging.getLogger(__name__).info("Logging initialized: %s", log_path)
    return log_path


def install_exception_hook():
    global _HOOK_INSTALLED
    if _HOOK_INSTALLED:
        return

    previous_hook = sys.excepthook

    def log_unhandled_exception(exc_type, exc, traceback):
        logging.getLogger(__name__).critical(
            "Unhandled exception",
            exc_info=(exc_type, exc, traceback),
        )
        previous_hook(exc_type, exc, traceback)

    sys.excepthook = log_unhandled_exception
    _HOOK_INSTALLED = True
