import logging

from app.gui.workers import FunctionWorker
from app.update_checker import UpdateCheckError


def raising(exc):
    def _raise():
        raise exc

    return _raise


def background_failure_records(caplog):
    return [
        record
        for record in caplog.records
        if record.name == "app.gui.workers" and "Background task failed" in record.message
    ]


def test_expected_update_check_errors_do_not_log_worker_traceback(caplog):
    caplog.set_level(logging.WARNING, logger="app.gui.workers")
    worker = FunctionWorker(raising(UpdateCheckError("Could not contact GitHub Releases.")))

    worker.run()

    records = background_failure_records(caplog)
    assert len(records) == 1
    assert not records[0].exc_info


def test_unexpected_background_errors_keep_traceback(caplog):
    caplog.set_level(logging.WARNING, logger="app.gui.workers")
    worker = FunctionWorker(raising(RuntimeError("unexpected worker failure")))

    worker.run()

    records = background_failure_records(caplog)
    assert len(records) == 1
    assert records[0].exc_info
