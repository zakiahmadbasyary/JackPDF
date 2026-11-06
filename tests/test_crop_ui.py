import os
import sys
import pymupdf as fitz
import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.main_window import MainWindow
from app.ui.pages.crop_page import CropPage
from app.utils.pdf_geometry import CropMargins


def create_test_pdf(path: str, pages: int = 4):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595.0, height=842.0)
        page.insert_text((50, 50), f"Halaman {i + 1}")
    doc.save(path)
    doc.close()


@pytest.fixture
def app():
    app_instance = QApplication.instance()
    if app_instance is None:
        app_instance = QApplication(sys.argv)
    return app_instance


def test_crop_ui_initial_state(app):
    page = CropPage()
    page.show()

    assert page.current_file is None
    assert page.current_page_count == 0
    assert page.drop_zone.isVisible() is True
    assert page.info_card.isVisible() is False
    assert page.settings_card.isVisible() is False
    assert page.result_card.isVisible() is False
    assert page.crop_btn.isEnabled() is False


def test_crop_ui_load_file_and_default_state(app, tmp_path):
    page = CropPage()
    page.show()
    pdf_path = str(tmp_path / "crop_doc.pdf")
    create_test_pdf(pdf_path, pages=3)

    page.load_pdf_file(pdf_path)

    assert page.current_file == os.path.abspath(pdf_path)
    assert page.current_page_count == 3
    assert page.current_page_num == 1
    assert page.drop_zone.isVisible() is False
    assert page.info_card.isVisible() is True
    assert page.settings_card.isVisible() is True
    assert page.crop_btn.isEnabled() is True

    # Check defaults
    assert page.radio_all_pages.isChecked() is True
    assert page.custom_pages_container.isVisible() is False
    assert page.get_selected_pages() == [1, 2, 3]

    # Margins are 0.0 mm
    assert page.current_margins.top_mm == 0.0
    assert page.current_margins.bottom_mm == 0.0
    assert page.current_margins.left_mm == 0.0
    assert page.current_margins.right_mm == 0.0

    # Page nav label
    assert "Hal 1 / 3" in page.page_nav_label.text()
    assert "209.9 × 297.0 mm" in page.orig_dim_label.text()


def test_crop_ui_margins_sync_and_center_crop(app, tmp_path):
    page = CropPage()
    page.show()
    pdf_path = str(tmp_path / "margins_test.pdf")
    create_test_pdf(pdf_path, pages=2)
    page.load_pdf_file(pdf_path)

    # Set margins via spinboxes
    page.top_spin.setValue(10.0)
    page.bottom_spin.setValue(20.0)
    page.left_spin.setValue(15.0)
    page.right_spin.setValue(25.0)

    assert page.current_margins.top_mm == 10.0
    assert page.current_margins.bottom_mm == 20.0
    assert page.current_margins.left_mm == 15.0
    assert page.current_margins.right_mm == 25.0
    assert page.canvas.margins.top_mm == 10.0

    # Center crop
    page.center_crop_btn.click()
    # Left and Right should become equal
    assert page.current_margins.left_mm == page.current_margins.right_mm
    # Top and Bottom should become equal
    assert page.current_margins.top_mm == page.current_margins.bottom_mm

    # Reset crop
    page.reset_crop_btn.click()
    assert page.current_margins.top_mm == 0.0
    assert page.current_margins.bottom_mm == 0.0
    assert page.current_margins.left_mm == 0.0
    assert page.current_margins.right_mm == 0.0


def test_crop_ui_page_selection_modes(app, tmp_path):
    page = CropPage()
    page.show()
    pdf_path = str(tmp_path / "pages_mode_test.pdf")
    create_test_pdf(pdf_path, pages=5)
    page.load_pdf_file(pdf_path)

    # 1. All pages
    assert page.get_selected_pages() == [1, 2, 3, 4, 5]

    # 2. Current page only
    page.radio_current_page.setChecked(True)
    assert page.get_selected_pages() == [1]

    # Navigate to next page and check current page updates
    page.next_page()
    assert page.current_page_num == 2
    assert page.get_selected_pages() == [2]

    # 3. Custom pages
    page.radio_custom_pages.setChecked(True)
    assert page.custom_pages_container.isVisible() is True

    page.manual_range_edit.setText("1, 3-4")
    assert page.get_selected_pages() == [1, 3, 4]
    assert page.page_error_label.isVisible() is False
    assert page.crop_btn.isEnabled() is True

    # Invalid range disables button
    page.manual_range_edit.setText("99")
    assert page.get_selected_pages() == []
    assert page.page_error_label.isVisible() is True
    assert page.crop_btn.isEnabled() is False


def test_crop_ui_excessive_margin_validation(app, tmp_path):
    page = CropPage()
    page.show()
    pdf_path = str(tmp_path / "excess_test.pdf")
    create_test_pdf(pdf_path, pages=1)
    page.load_pdf_file(pdf_path)

    # A4 width is 210mm. Setting left + right to 120 + 120 = 240mm exceeds width!
    page.left_spin.setValue(120.0)
    page.right_spin.setValue(120.0)

    assert page.margin_error_label.isVisible() is True
    assert page.crop_btn.isEnabled() is False


def test_crop_ui_zoom_controls(app, tmp_path):
    page = CropPage()
    page.show()
    pdf_path = str(tmp_path / "zoom_test.pdf")
    create_test_pdf(pdf_path, pages=1)
    page.load_pdf_file(pdf_path)

    orig_zoom = page.zoom_factor
    page.zoom_in()
    assert page.zoom_factor > orig_zoom

    page.zoom_out()
    page.zoom_out()
    assert page.zoom_factor < orig_zoom

    page.zoom_fit()
    assert page.zoom_factor == 1.0


def test_crop_ui_worker_finished(app, tmp_path):
    page = CropPage()
    page.show()
    pdf_path = str(tmp_path / "done_test.pdf")
    create_test_pdf(pdf_path, pages=2)
    page.load_pdf_file(pdf_path)

    mock_result = {
        "output_path": str(tmp_path / "done_test_cropped.pdf"),
        "total_pages": 2,
        "total_requested": 2,
        "total_cropped": 2,
        "cropped_pages": [1, 2],
        "failed_pages": [],
        "margins": CropMargins(5, 5, 5, 5),
        "is_cancelled": False,
    }

    page.on_worker_finished(True, "Berhasil memotong 2 halaman dokumen.", mock_result)
    assert page.result_card.isVisible() is True
    assert "2 halaman" in page.result_details_label.text()
    assert "done_test_cropped.pdf" in page.result_details_label.text()


def test_crop_ui_reset_form(app, tmp_path):
    page = CropPage()
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
    assert page.crop_btn.isEnabled() is False


def test_main_window_navigation_to_crop(app):
    win = MainWindow()

    # Navigate to Crop PDF via nav button
    win.show_crop()
    assert win.content.currentWidget() == win.crop_page
    assert win.nav_buttons["Crop PDF"].property("active") == "true"

    # Go back to home
    win.crop_page.go_back.emit()
    assert win.content.currentWidget() == win.home_page

    # Feature selected from home
    win.on_feature_selected("Crop PDF")
    assert win.content.currentWidget() == win.crop_page
