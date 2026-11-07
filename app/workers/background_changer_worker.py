"""
background_changer_worker.py - Background thread for AI background removal in JackPDF.
"""

from typing import Optional
from PIL import Image
from PySide6.QtCore import QThread, Signal

from app.services.background_changer_service import (
    load_and_orient_image,
    remove_background,
)


class BackgroundChangerWorker(QThread):
    """
    QThread worker to execute AI background removal without blocking the GUI.
    """
    progress = Signal(str)
    finished = Signal(bool, str, object)  # (success, message, result_fg_image)

    def __init__(
        self,
        image_path: str,
        model_name: str = "u2netp",
        parent=None,
    ):
        super().__init__(parent)
        self.image_path = image_path
        self.model_name = model_name
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self._is_cancelled:
                self.finished.emit(False, "Proses dibatalkan.", None)
                return

            self.progress.emit("Mempersiapkan gambar dan menginisialisasi model AI...")
            img = load_and_orient_image(self.image_path)

            if self._is_cancelled:
                self.finished.emit(False, "Proses dibatalkan.", None)
                return

            self.progress.emit("Menghapus background menggunakan AI...")
            result_fg = remove_background(img, model_name=self.model_name)

            if self._is_cancelled:
                self.finished.emit(False, "Proses dibatalkan.", None)
                return

            self.progress.emit("Pemotongan background selesai.")
            self.finished.emit(True, "", result_fg)

        except Exception as e:
            self.finished.emit(False, f"Terjadi kesalahan saat memproses gambar: {str(e)}", None)

