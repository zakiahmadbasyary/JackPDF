"""
convert_images_to_pdf_worker.py - Background worker thread for JackPDF Convert Images to PDF.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import QThread, Signal

from app.services.convert_images_to_pdf_service import convert_images_to_pdf


class ConvertImagesToPdfWorker(QThread):
    """
    Background worker thread to assemble images into a PDF document asynchronously
    without freezing the user interface, with full cancellation support.
    """

    progress = Signal(int, int, str)       # current, total, status_message
    finished = Signal(bool, str, object)   # success, message, result_data

    def __init__(
        self,
        image_paths: List[str],
        output_path: str,
        page_format: str = "fit_to_image",
        margin_mm: float = 0.0,
    ):
        super().__init__()
        self.image_paths = image_paths
        self.output_path = output_path
        self.page_format = page_format
        self.margin_mm = margin_mm
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
            success, message, result_data = convert_images_to_pdf(
                image_paths=self.image_paths,
                output_path=self.output_path,
                page_format=self.page_format,
                margin_mm=self.margin_mm,
                progress_callback=on_progress,
                is_cancelled_callback=is_cancelled,
            )
            self.finished.emit(success, message, result_data)
        except Exception as e:
            self.finished.emit(
                False, f"Terjadi kesalahan saat konversi: {str(e)}", None
            )

