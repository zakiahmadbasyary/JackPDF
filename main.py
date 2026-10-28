import sys

from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JackPDF")
    app.setOrganizationName("JackPDF")

    with open("assets/styles/light.qss", "r", encoding="utf-8") as style_file:
        app.setStyleSheet(style_file.read())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
