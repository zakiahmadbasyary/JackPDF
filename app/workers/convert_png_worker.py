from typing import Any, List, Optional
from PySide6.QtCore import QThread, Signal

from app.services.convert_png_service import convert_pdf_to_png


class ConvertPngWorker(QThread):
    """
    Background worker thread to convert PDF pages to PNG asynchronously
    without freezing the user interface, with safe cancellation support.
    """

    progress = Signal(int, int, str)  # current, total, status_message
    finished = Signal(bool, str, object)  # success, message, result_data

    def __init__(
        self,
        input_path: str,
        output_dir: str,
        pages: Optional[List[int]] = None,
        dpi: int = 200,
        color_mode: str = "rgb",
        password: Optional[str] = None,
    ):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir
        self.pages = pages
        self.dpi = dpi
        self.color_mode = color_mode
        self.password = password
        self._is_cancelled = False

    def cancel(self) -> None:
        """Signal the worker to safely stop processing subsequent pages."""
        self._is_cancelled = True

    def run(self) -> None:
        def on_progress(current: int, total: int, message: str) -> None:
            self.progress.emit(current, total, message)

        def is_cancelled() -> bool:
            return self._is_cancelled

        try:
            success, message, result_data = convert_pdf_to_png(
                input_path=self.input_path,
                output_dir=self.output_dir,
                pages=self.pages,
                dpi=self.dpi,
                color_mode=self.color_mode,
                password=self.password,
                progress_callback=on_progress,
                is_cancelled_callback=is_cancelled,
            )
            self.finished.emit(success, message, result_data)
        except Exception as e:
            self.finished.emit(
                False, f"Terjadi kesalahan saat pemrosesan: {str(e)}", None
            )

