__all__ = ["BPOverviewTab"]


def __getattr__(name):
    if name == "BPOverviewTab":
        from .bp_overview_tab import BPOverviewTab

        return BPOverviewTab

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
