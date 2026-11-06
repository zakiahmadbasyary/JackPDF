import os
import sys

from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow
from app.utils.icon_utils import get_app_icon
from app.utils.resource_utils import get_resource_path


def main():
    # Set Windows taskbar explicit app user model ID for proper icon display
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("jackpdf.app.desktop")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("JackPDF")
    app.setOrganizationName("JackPDF")
    app.setWindowIcon(get_app_icon())

    qss_path = get_resource_path("assets/styles/light.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as style_file:
            app.setStyleSheet(style_file.read())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
