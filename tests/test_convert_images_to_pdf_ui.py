import os
import sys
from PIL import Image
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.main_window import MainWindow
from app.ui.pages.convert_images_to_pdf_page import ConvertImagesToPdfPage


def create_sample_image(path: str, size: tuple[int, int] = (200, 100)) -> str:
    img = Image.new("RGB", size, (255, 128, 0))
    img.save(path)
    return path


@pytest.fixture
def app():
    app_instance = QApplication.instance()
    if app_instance is None:
        app_instance = QApplication(sys.argv)
    return app_instance


def test_ui_initial_state(app):
    page = ConvertImagesToPdfPage()
    page.show()

    assert len(page.image_list) == 0
    assert page.drop_zone.isVisible() is True
    assert page.toolbar_widget.isVisible() is False
    assert page.table.isVisible() is False
    assert page.settings_card.isVisible() is False
    assert page.convert_btn.isEnabled() is False


def test_ui_add_images_and_table(app, tmp_path):
    page = ConvertImagesToPdfPage()
    page.show()

    img1 = create_sample_image(str(tmp_path / "img1.png"), (300, 200))
    img2 = create_sample_image(str(tmp_path / "img2.jpg"), (400, 500))

    page.add_images([img1, img2])

    assert len(page.image_list) == 2
    assert page.table.rowCount() == 2
    assert page.drop_zone.isVisible() is False
    assert page.toolbar_widget.isVisible() is True
    assert page.table.isVisible() is True
    assert page.settings_card.isVisible() is True
    assert page.convert_btn.isEnabled() is True

    # Test duplicate prevention
    page.add_images([img1])
    assert len(page.image_list) == 2
    assert page.table.rowCount() == 2


def test_ui_reorder_and_remove(app, tmp_path):
    page = ConvertImagesToPdfPage()
    page.show()

    img1 = create_sample_image(str(tmp_path / "img1.png"))
    img2 = create_sample_image(str(tmp_path / "img2.jpg"))
    img3 = create_sample_image(str(tmp_path / "img3.png"))

    page.add_images([img1, img2, img3])
    assert [item["path"] for item in page.image_list] == [os.path.abspath(img1), os.path.abspath(img2), os.path.abspath(img3)]

    # Select second row (img2) and move up
    page.table.selectRow(1)
    page.move_up()
    assert [item["path"] for item in page.image_list] == [os.path.abspath(img2), os.path.abspath(img1), os.path.abspath(img3)]

    # Move down
    page.move_down()
    assert [item["path"] for item in page.image_list] == [os.path.abspath(img1), os.path.abspath(img2), os.path.abspath(img3)]

    # Remove selected row (row 1 is img2)
    page.table.selectRow(1)
    page.remove_selected()
    assert len(page.image_list) == 2
    assert [item["path"] for item in page.image_list] == [os.path.abspath(img1), os.path.abspath(img3)]

    # Clear all
    page.clear_all()
    assert len(page.image_list) == 0
    assert page.table.rowCount() == 0
    assert page.drop_zone.isVisible() is True
    assert page.toolbar_widget.isVisible() is False
    assert page.table.isVisible() is False
    assert page.convert_btn.isEnabled() is False


def test_ui_reset_form(app, tmp_path):
    page = ConvertImagesToPdfPage()
    page.show()

    img = create_sample_image(str(tmp_path / "img.png"))
    page.add_images([img])
    assert len(page.image_list) == 1
    assert page.table.isVisible() is True

    # Change settings
    page.filename_edit.setText("Custom_Name.pdf")
    page.radio_a4_p.setChecked(True)
    page.radio_m_std.setChecked(True)

    # Click reset button
    page.reset_btn.click()

    assert len(page.image_list) == 0
    assert page.table.rowCount() == 0
    assert page.drop_zone.isVisible() is True
    assert page.table.isVisible() is False
    assert page.filename_edit.text() == "Converted_Images.pdf"
    assert page.radio_fit.isChecked() is True
    assert page.radio_m_none.isChecked() is True


def test_main_window_navigation_to_image_to_pdf(app):
    window = MainWindow()
    window.show()

    # Home page contains "Image to PDF" card
    card_names = [card.title for card in window.home_page.cards]
    assert "Image to PDF" in card_names

    # Navigate from home page signal
    window.home_page.feature_selected.emit("Image to PDF")
    assert window.content.currentWidget() == window.convert_images_to_pdf_page

    # Go back to home
    window.convert_images_to_pdf_page.go_back.emit()
    assert window.content.currentWidget() == window.home_page

    # Navigate via sidebar button
    nav_btn = window.nav_buttons.get("Image to PDF")
    assert nav_btn is not None
    nav_btn.click()
    assert window.content.currentWidget() == window.convert_images_to_pdf_page
