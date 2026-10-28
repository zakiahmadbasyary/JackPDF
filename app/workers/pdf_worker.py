from typing import Any, Callable
from PySide6.QtCore import QThread, Signal


class PdfTaskWorker(QThread):
    """
    Background worker thread to run PDF tasks asynchronously
    and avoid freezing the UI.
    """

    progress = Signal(int, int, str)  # current, total, message
    finished = Signal(bool, str, object)  # success, message, result_data

    def __init__(self, task_fn: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__()
        self.task_fn = task_fn
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        def on_progress(current: int, total: int, message: str) -> None:
            self.progress.emit(current, total, message)

        try:
            # Inject progress callback into task function kwargs
            self.kwargs["progress_callback"] = on_progress
            result = self.task_fn(*self.args, **self.kwargs)
            if isinstance(result, tuple) and len(result) >= 2:
                success = bool(result[0])
                message = str(result[1])
                data = result[2] if len(result) >= 3 else None
                self.finished.emit(success, message, data)
            else:
                self.finished.emit(True, "Operasi selesai.", result)
        except Exception as e:
            self.finished.emit(
                False, f"Terjadi kesalahan saat pemrosesan: {str(e)}", None
            )
