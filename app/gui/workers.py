import logging

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(object)
    finished = Signal()


class FunctionWorker(QRunnable):
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            self.signals.result.emit(self.function(*self.args, **self.kwargs))
        except Exception as exc:
            logger.warning(
                "Background task failed: %s",
                exc,
                exc_info=not getattr(exc, "suppress_worker_traceback", False),
            )
            self.signals.error.emit(exc)
        finally:
            self.signals.finished.emit()


class BackgroundTaskMixin:
    def start_background_task(self, function, on_result=None, on_error=None, on_finished=None):
        if not hasattr(self, "_background_workers"):
            self._background_workers = set()

        worker = FunctionWorker(function)
        self._background_workers.add(worker)

        if on_result:
            worker.signals.result.connect(on_result)
        if on_error:
            worker.signals.error.connect(on_error)
        if on_finished:
            worker.signals.finished.connect(on_finished)
        worker.signals.finished.connect(lambda completed=worker: self._background_workers.discard(completed))

        QThreadPool.globalInstance().start(worker)
        return worker
