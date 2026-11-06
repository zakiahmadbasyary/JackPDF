import os
import sys
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.main_window import MainWindow
from app.services.settings_service import SettingsService, get_settings_service
from app.ui.dialogs.settings_dialog import SettingsDialog


@pytest.fixture
def app():
    app_instance = QApplication.instance()
    if app_instance is None:
        app_instance = QApplication(sys.argv)
    return app_instance


def test_settings_service_defaults():
    service = SettingsService()
    service.reset_to_defaults()

    assert service.get("output_mode") == "source"
    assert service.get("conflict_action") == "confirm"
    assert service.get("auto_open_folder") is False
    assert service.get("auto_open_file") is False
    assert service.get("default_png_dpi") == 200
    assert service.get("default_png_color") == "rgb"
    assert service.get("default_compress_preset") == "recommended"
    assert service.get("default_crop_unit") == "mm"


def test_settings_service_set_and_get():
    service = SettingsService()

    service.set("default_png_dpi", 300)
    assert service.get("default_png_dpi") == 300

    service.set("auto_open_folder", True)
    assert service.get("auto_open_folder") is True

    # Reset back
    service.reset_to_defaults()
    assert service.get("default_png_dpi") == 200
    assert service.get("auto_open_folder") is False


def test_settings_service_clear_cache():
    service = SettingsService()
    count = service.clear_cache()
    assert isinstance(count, int)
    assert count >= 0


def test_settings_dialog_tabs_and_controls(app):
    dialog = SettingsDialog()
    assert dialog.tabs.count() == 3
    assert dialog.tabs.tabText(0) == "Penyimpanan"
    assert dialog.tabs.tabText(1) == "Preferensi Alat"
    assert dialog.tabs.tabText(2) == "Tentang JackPDF"

    # Default output is source
    assert dialog.radio_out_source.isChecked() is True
    assert dialog.custom_dir_edit.isEnabled() is False

    # Toggle custom
    dialog.radio_out_custom.setChecked(True)
    assert dialog.custom_dir_edit.isEnabled() is True
    assert dialog.browse_dir_btn.isEnabled() is True


def test_settings_dialog_save(app, tmp_path):
    dialog = SettingsDialog()

    # Change some values
    dialog.radio_out_custom.setChecked(True)
    custom_dir = str(tmp_path / "custom_out")
    os.makedirs(custom_dir, exist_ok=True)
    dialog.custom_dir_edit.setText(custom_dir)

    dialog.radio_conflict_auto.setChecked(True)
    dialog.cb_auto_folder.setChecked(True)

    # Save
    dialog._on_save_clicked()

    # Check that service has new values
    service = get_settings_service()
    assert service.get("output_mode") == "custom"
    assert service.get("custom_output_dir") == custom_dir
    assert service.get("conflict_action") == "auto_number"
    assert service.get("auto_open_folder") is True

    # Reset back
    service.reset_to_defaults()


def test_main_window_settings_button(app):
    win = MainWindow()
    assert hasattr(win, "sidebar_settings_btn")
    assert hasattr(win.home_page, "settings_btn")
    assert win.sidebar_settings_btn.text().strip() == "⚙  Pengaturan"


def test_effective_output_dir(tmp_path):
    from app.services.settings_service import get_effective_output_dir

    service = get_settings_service()
    service.reset_to_defaults()

    dummy_source = str(tmp_path / "source_dir" / "doc.pdf")
    os.makedirs(os.path.dirname(dummy_source), exist_ok=True)
    with open(dummy_source, "w") as f:
        f.write("dummy")

    # Mode 'source'
    eff = get_effective_output_dir(dummy_source)
    assert eff == os.path.dirname(dummy_source)

    # Mode 'custom'
    custom_dir = str(tmp_path / "custom_output")
    os.makedirs(custom_dir, exist_ok=True)
    service.set("output_mode", "custom")
    service.set("custom_output_dir", custom_dir)

    eff_custom = get_effective_output_dir(dummy_source)
    assert eff_custom == os.path.abspath(custom_dir)

    service.reset_to_defaults()


def test_feature_pages_respect_custom_output_dir(app, tmp_path):
    from app.services.settings_service import get_settings_service
    from app.ui.pages.compress_page import CompressPage
    from app.ui.pages.crop_page import CropPage
    from app.ui.pages.convert_png_page import ConvertPngPage
    import fitz

    # Create dummy pdf
    sample_pdf = str(tmp_path / "sample.pdf")
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(sample_pdf)
    doc.close()

    # Set custom output dir
    custom_dir = str(tmp_path / "my_custom_folder")
    os.makedirs(custom_dir, exist_ok=True)

    service = get_settings_service()
    service.set("output_mode", "custom")
    service.set("custom_output_dir", custom_dir)

    # 1. CompressPage
    comp_page = CompressPage()
    comp_page.load_pdf_file(sample_pdf)
    assert comp_page.current_output_dir == os.path.abspath(custom_dir)
    assert comp_page.output_dir_label.text() == os.path.abspath(custom_dir)

    # 2. CropPage
    crop_page = CropPage()
    crop_page.load_pdf_file(sample_pdf)
    assert crop_page.output_dir_edit.text() == os.path.abspath(custom_dir)

    # 3. ConvertPngPage
    png_page = ConvertPngPage()
    png_page.load_pdf_file(sample_pdf)
    expected_png_folder = os.path.join(os.path.abspath(custom_dir), "sample_png")
    assert png_page.current_output_dir == expected_png_folder
    assert png_page.output_dir_label.text() == expected_png_folder

    # Clean up
    service.reset_to_defaults()
