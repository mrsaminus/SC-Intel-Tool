__all__ = ["MainWindow", "run_app"]


def __getattr__(name):
    if name in __all__:
        from .main_window import MainWindow, run_app

        exports = {
            "MainWindow": MainWindow,
            "run_app": run_app,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
