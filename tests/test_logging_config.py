import logging

from conftest import reload_module


def test_configure_logging_creates_local_rotating_log(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SC_INTEL_DATA_DIR", str(data_dir))
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if getattr(handler, "_sc_intel_tool_handler", False):
            root_logger.removeHandler(handler)
            handler.close()

    logging_config = reload_module("app.logging_config")
    log_path = logging_config.configure_logging()

    logging.getLogger("tests.logging").info("alpha hardening log smoke")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_path == data_dir / "logs" / "sc_intel_tool.log"
    assert log_path.exists()
    assert "alpha hardening log smoke" in log_path.read_text(encoding="utf-8")


def test_exception_hook_install_is_idempotent():
    import app.logging_config as logging_config

    original_hook = logging_config.sys.excepthook
    logging_config.install_exception_hook()
    first_hook = logging_config.sys.excepthook
    logging_config.install_exception_hook()

    try:
        assert logging_config.sys.excepthook is first_hook
    finally:
        logging_config.sys.excepthook = original_hook
        logging_config._HOOK_INSTALLED = False
