"""
crop_worker.py - Background worker thread for JackPDF Crop PDF feature.
"""

from typing import Any, List, Optional
from PySide6.QtCore import QThread, Signal

from app.services.crop_service import crop_pdf
from app.utils.pdf_geometry import CropMargins


class CropWorker(QThread):
    """
    Background worker thread to crop PDF pages asynchronously
    without freezing the user interface, with safe cancellation support.
    """

    progress = Signal(int, int, str)       # current, total, status_message
    finished = Signal(bool, str, object)   # success, message, result_data

    def __init__(
        self,
        input_path: str,
        output_path: str,
        margins: CropMargins,
        pages: Optional[List[int]] = None,
        password: Optional[str] = None,
    ):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.margins = margins
        self.pages = pages
        self.password = password
        self._is_cancelled = False

    def cancel(self) -> None:
        """Signal the worker to safely stop processing."""
        self._is_cancelled = True

    def run(self) -> None:
        def on_progress(current: int, total: int, message: str) -> None:
            self.progress.emit(current, total, message)

        def is_cancelled() -> bool:
            return self._is_cancelled

        try:
            success, message, result_data = crop_pdf(
                input_path=self.input_path,
                output_path=self.output_path,
                margins=self.margins,
                pages=self.pages,
                password=self.password,
                progress_callback=on_progress,
                is_cancelled_callback=is_cancelled,
            )
            self.finished.emit(success, message, result_data)
        except Exception as e:
            self.finished.emit(
                False, f"Terjadi kesalahan saat pemrosesan crop: {str(e)}", None
            )

