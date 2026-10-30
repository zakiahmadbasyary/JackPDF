import os
import sys
from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"


def test_app_and_main_window():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    with open("assets/styles/light.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    from app.main_window import MainWindow

    window = MainWindow()
    assert window.windowTitle() == "JackPDF"
    assert window.centralWidget() is not None


def test_responsive_grid_reflow():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    from app.ui.home_page import HomePage

    home = HomePage()

    # Small size -> 1 column
    home.resizeEvent(QResizeEvent(QSize(400, 600), QSize(800, 600)))
    assert home.current_cols == 1

    # Medium size -> 2 columns
    home.resizeEvent(QResizeEvent(QSize(750, 600), QSize(400, 600)))
    assert home.current_cols == 2

    # Large size -> 3 columns
    home.resizeEvent(QResizeEvent(QSize(1150, 700), QSize(750, 600)))
    assert home.current_cols == 3

    # Extra large size -> 4 columns
    home.resizeEvent(QResizeEvent(QSize(1600, 900), QSize(1150, 700)))
    assert home.current_cols == 4


def test_feature_card_clickable():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    from app.ui.home_page import FeatureCard
    from PySide6.QtCore import Qt, QPointF
    from PySide6.QtGui import QMouseEvent

    card = FeatureCard("Merge PDF", "Gabungkan PDF", "Tooltip")
    selected_features = []
    card.selected.connect(selected_features.append)

    # Click card directly
    ev = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    card.mousePressEvent(ev)
    assert selected_features == ["Merge PDF"]

