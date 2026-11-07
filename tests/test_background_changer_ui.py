import os
import sys
from PIL import Image
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.main_window import MainWindow
from app.ui.pages.background_changer_page import BackgroundChangerPage


def create_sample_image(path: str, size: tuple[int, int] = (200, 250)) -> str:
    img = Image.new("RGB", size, (220, 100, 50))
    img.save(path)
    return path


@pytest.fixture
def app():
    app_instance = QApplication.instance()
    if app_instance is None:
        app_instance = QApplication(sys.argv)
    return app_instance


def test_ui_initial_state(app):
    page = BackgroundChangerPage()
    page.show()

    assert page.current_image_path is None
    assert page.drop_zone.isVisible() is True
    assert page.workspace_widget.isVisible() is False
    assert page.selected_color_key == "Merah"
    assert page.current_mode == "formal"


def test_ui_load_image(app, tmp_path):
    page = BackgroundChangerPage()
    page.show()

    img_path = create_sample_image(str(tmp_path / "foto.jpg"), (300, 400))
    page.load_image_file(img_path)

    assert page.current_image_path == os.path.abspath(img_path)
    assert page.drop_zone.isVisible() is False
    assert page.workspace_widget.isVisible() is True
    assert "foto.jpg" in page.file_name_label.text()
    assert "300 × 400 px" in page.file_meta_label.text()
    assert page.remove_bg_btn.isEnabled() is True
    assert page.save_jpg_btn.isEnabled() is False


def test_ui_color_selection(app, tmp_path):
    page = BackgroundChangerPage()
    page.show()

    img_path = create_sample_image(str(tmp_path / "foto.jpg"))
    page.load_image_file(img_path)

    # Change color to Biru
    page.select_background_color("Biru")
    assert page.selected_color_key == "Biru"
    assert page.swatch_widgets["Biru"].is_active is True
    assert page.swatch_widgets["Merah"].is_active is False

    # Change color to Hijau
    page.select_background_color("Hijau")
    assert page.selected_color_key == "Hijau"
    assert page.swatch_widgets["Hijau"].is_active is True
    assert page.swatch_widgets["Biru"].is_active is False


def test_ui_mode_toggle(app, tmp_path):
    page = BackgroundChangerPage()
    page.show()

    img_path = create_sample_image(str(tmp_path / "foto.jpg"))
    page.load_image_file(img_path)

    # Default is formal: pas foto container is visible
    assert page.radio_mode_formal.isChecked() is True
    assert page.pas_foto_container.isVisible() is True

    # Switch to free mode
    page.radio_mode_free.setChecked(True)
    assert page.current_mode == "free"
    assert page.pas_foto_container.isVisible() is False

    # Switch back to formal mode
    page.radio_mode_formal.setChecked(True)
    assert page.current_mode == "formal"
    assert page.pas_foto_container.isVisible() is True


def test_ui_reset(app, tmp_path):
    page = BackgroundChangerPage()
    page.show()

    img_path = create_sample_image(str(tmp_path / "foto.jpg"))
    page.load_image_file(img_path)

    assert page.drop_zone.isVisible() is False
    assert page.workspace_widget.isVisible() is True

    # Click reset
    page.reset_form()
    assert page.current_image_path is None
    assert page.drop_zone.isVisible() is True
    assert page.workspace_widget.isVisible() is False


def test_navigation_integration(app):
    window = MainWindow()
    window.show()

    # Initial page is home
    assert window.content.currentWidget() == window.home_page

    # Click Background Changer in sidebar
    window.show_background_changer()
    assert window.content.currentWidget() == window.background_changer_page

    # Go back to home
    window.background_changer_page.go_back.emit()
    assert window.content.currentWidget() == window.home_page

    # Select Background Changer via feature_selected signal (e.g. from Home card)
    window.on_feature_selected("Background Changer")
    assert window.content.currentWidget() == window.background_changer_page

