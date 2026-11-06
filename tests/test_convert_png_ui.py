import os
import sys
import pymupdf as fitz
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.main_window import MainWindow
from app.ui.pages.convert_png_page import ConvertPngPage


def create_test_pdf(path: str, pages: int = 5):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Halaman {i + 1}")
    doc.save(path)
    doc.close()


@pytest.fixture
def app():
    app_instance = QApplication.instance()
    if app_instance is None:
        app_instance = QApplication(sys.argv)
    return app_instance


def test_convert_ui_initial_state(app):
    page = ConvertPngPage()
    page.show()

    assert page.current_file is None
    assert page.current_page_count == 0
    assert page.drop_zone.isVisible() is True
    assert page.info_card.isVisible() is False
    assert page.settings_card.isVisible() is False
    assert page.result_card.isVisible() is False
    assert page.convert_btn.isEnabled() is False


def test_convert_ui_load_file_and_default_all_pages(app, tmp_path):
    page = ConvertPngPage()
    page.show()
    pdf_path = str(tmp_path / "doc_test.pdf")
    create_test_pdf(pdf_path, pages=4)

    page.load_pdf_file(pdf_path)

    assert page.current_file == os.path.abspath(pdf_path)
    assert page.current_page_count == 4
    assert page.drop_zone.isVisible() is False
    assert page.info_card.isVisible() is True
    assert page.settings_card.isVisible() is True
    assert page.convert_btn.isEnabled() is True

    # By default 'Semua Halaman' is checked and custom input container is hidden
    assert page.radio_all_pages.isChecked() is True
    assert page.custom_pages_container.isVisible() is False
    assert page.get_selected_pages() == [1, 2, 3, 4]


def test_convert_ui_custom_page_mode_and_typing(app, tmp_path):
    page = ConvertPngPage()
    page.show()
    pdf_path = str(tmp_path / "sync_test.pdf")
    create_test_pdf(pdf_path, pages=6)

    page.load_pdf_file(pdf_path)

    # Switch to 'Pilih Halaman Tertentu'
    page.radio_custom_pages.setChecked(True)
    assert page.custom_pages_container.isVisible() is True

    # Type '1, 3-4, 6'
    page.manual_range_edit.setText("1, 3-4, 6")
    assert page.get_selected_pages() == [1, 3, 4, 6]
    assert page.manual_error_label.isVisible() is False
    assert "4 dari 6" in page.page_summary_label.text()
    assert page.convert_btn.isEnabled() is True


def test_convert_ui_manual_range_validation_errors(app, tmp_path):
    page = ConvertPngPage()
    page.show()
    pdf_path = str(tmp_path / "manual_test.pdf")
    create_test_pdf(pdf_path, pages=5)

    page.load_pdf_file(pdf_path)
    page.radio_custom_pages.setChecked(True)

    # Out of range page number
    page.manual_range_edit.setText("1, 2, 8")
    assert page.get_selected_pages() == []
    assert page.manual_error_label.isVisible() is True
    assert page.convert_btn.isEnabled() is False

    # Inverted range (4-2)
    page.manual_range_edit.setText("4-2")
    assert page.get_selected_pages() == []
    assert page.manual_error_label.isVisible() is True
    assert page.convert_btn.isEnabled() is False

    # Fix to valid range
    page.manual_range_edit.setText("2-4")
    assert page.get_selected_pages() == [2, 3, 4]
    assert page.manual_error_label.isVisible() is False
    assert page.convert_btn.isEnabled() is True


def test_convert_ui_dpi_and_color_mode_options(app, tmp_path):
    page = ConvertPngPage()
    page.show()
    pdf_path = str(tmp_path / "opts_test.pdf")
    create_test_pdf(pdf_path, pages=1)
    page.load_pdf_file(pdf_path)

    # Default DPI is 200
    assert page.get_selected_dpi() == 200

    # 150 DPI
    page.radio_dpi_150.setChecked(True)
    assert page.get_selected_dpi() == 150

    # 300 DPI
    page.radio_dpi_300.setChecked(True)
    assert page.get_selected_dpi() == 300

    # Custom DPI
    page.radio_dpi_custom.setChecked(True)
    assert page.custom_dpi_spin.isEnabled() is True
    page.custom_dpi_spin.setValue(250)
    assert page.get_selected_dpi() == 250

    # Color mode
    assert page.get_selected_color_mode() == "rgb"
    page.radio_color_gray.setChecked(True)
    assert page.get_selected_color_mode() == "grayscale"


def test_convert_ui_worker_finished(app, tmp_path):
    page = ConvertPngPage()
    page.show()
    pdf_path = str(tmp_path / "done_test.pdf")
    create_test_pdf(pdf_path, pages=2)
    page.load_pdf_file(pdf_path)

    mock_result = {
        "generated_files": ["f1.png", "f2.png"],
        "failed_pages": [],
        "total_requested": 2,
        "total_success": 2,
        "output_dir": str(tmp_path / "done_png"),
        "dpi": 200,
        "color_mode": "rgb",
        "is_cancelled": False,
    }

    page.on_worker_finished(True, "Selesai", mock_result)
    assert page.result_card.isVisible() is True
    assert "2 dari 2 halaman" in page.result_details_label.text()


def test_convert_ui_reset_form(app, tmp_path):
    page = ConvertPngPage()
    page.show()
    pdf_path = str(tmp_path / "reset_test.pdf")
    create_test_pdf(pdf_path, pages=2)
    page.load_pdf_file(pdf_path)

    page.reset_form()
    assert page.current_file is None
    assert page.current_page_count == 0
    assert page.drop_zone.isVisible() is True
    assert page.info_card.isVisible() is False
    assert page.settings_card.isVisible() is False
    assert page.result_card.isVisible() is False
    assert page.convert_btn.isEnabled() is False


def test_main_window_navigation_to_convert_png(app):
    win = MainWindow()

    # Navigate to Convert to PNG
    win.show_convert_png()
    assert win.content.currentWidget() == win.convert_png_page
    assert win.nav_buttons["Convert to PNG"].property("active") == "true"

    # Return to home
    win.convert_png_page.go_back.emit()
    assert win.content.currentWidget() == win.home_page

    # Feature selection from home
    win.on_feature_selected("Convert to PNG")
    assert win.content.currentWidget() == win.convert_png_page
