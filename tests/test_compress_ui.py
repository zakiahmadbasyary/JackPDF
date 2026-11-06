import os
import sys
import pymupdf as fitz
import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.main_window import MainWindow
from app.ui.pages.compress_page import CompressPage


def create_test_pdf(path: str, pages: int = 2):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i + 1} content")
    doc.save(path)
    doc.close()


@pytest.fixture
def app():
    app_instance = QApplication.instance()
    if app_instance is None:
        app_instance = QApplication(sys.argv)
    return app_instance


def test_compress_page_initial_state(app):
    page = CompressPage()
    page.show()

    assert page.current_file is None
    assert page.current_page_count == 0
    assert page.selected_preset == "balanced"

    # UI element visibilities
    assert page.drop_zone.isVisible() is True
    assert page.info_card.isVisible() is False
    assert page.settings_card.isVisible() is False
    assert page.result_card.isVisible() is False
    assert page.preview_panel.isVisible() is False
    assert page.compress_btn.isEnabled() is False


def test_compress_page_load_file(app, tmp_path):
    page = CompressPage()
    page.show()
    pdf_path = str(tmp_path / "sample_doc.pdf")
    create_test_pdf(pdf_path, pages=3)

    page.load_pdf_file(pdf_path)

    assert page.current_file == os.path.abspath(pdf_path)
    assert page.current_page_count == 3
    assert page.drop_zone.isVisible() is False
    assert page.info_card.isVisible() is True
    assert page.settings_card.isVisible() is True
    assert page.compress_btn.isEnabled() is True

    # Output defaults
    assert page.output_name_edit.text() == "sample_doc_compressed.pdf"
    assert page.current_output_dir == os.path.dirname(os.path.abspath(pdf_path))
    assert "sample_doc.pdf" in page.file_details_label.text()
    assert "3 Halaman" in page.file_details_label.text()


def test_compress_page_preset_selection(app):
    page = CompressPage()
    page.show()

    # Default is balanced
    assert page.selected_preset == "balanced"
    assert page.preset_cards["balanced"].radio.isChecked() is True
    assert page.preset_cards["high"].radio.isChecked() is False
    assert page.preset_cards["small"].radio.isChecked() is False

    # Select high
    page.select_preset("high")
    assert page.selected_preset == "high"
    assert page.preset_cards["high"].radio.isChecked() is True
    assert page.preset_cards["balanced"].radio.isChecked() is False

    # Select small
    page.select_preset("small")
    assert page.selected_preset == "small"
    assert page.preset_cards["small"].radio.isChecked() is True
    assert page.preset_cards["high"].radio.isChecked() is False


def test_compress_page_reset_form(app, tmp_path):
    page = CompressPage()
    page.show()
    pdf_path = str(tmp_path / "doc_to_reset.pdf")
    create_test_pdf(pdf_path, pages=1)

    page.load_pdf_file(pdf_path)
    page.select_preset("small")
    assert page.current_file is not None

    page.reset_form()
    assert page.current_file is None
    assert page.current_page_count == 0
    assert page.selected_preset == "balanced"
    assert page.info_card.isVisible() is False
    assert page.settings_card.isVisible() is False
    assert page.result_card.isVisible() is False
    assert page.drop_zone.isVisible() is True
    assert page.compress_btn.isEnabled() is False


def test_compress_page_worker_finished_success(app, tmp_path):
    page = CompressPage()
    page.show()
    pdf_path = str(tmp_path / "original.pdf")
    out_path = str(tmp_path / "compressed.pdf")
    create_test_pdf(pdf_path, pages=2)
    create_test_pdf(out_path, pages=2)

    page.load_pdf_file(pdf_path)

    mock_metrics = {
        "original_size": 204800,
        "compressed_size": 102400,
        "saved_bytes": 102400,
        "change_percent": 50.0,
        "is_larger": False,
        "is_same": False,
        "summary_text": "Hemat 100.0 KB (50.0%)",
        "output_path": out_path,
        "page_count": 2,
    }

    page.on_worker_finished(True, "Operasi berhasil", mock_metrics)

    assert page.result_card.isVisible() is True
    assert page.last_compressed_file == out_path
    assert "Hemat" in page.savings_badge.text()
    assert page.larger_note_label.isVisible() is False


def test_compress_page_worker_finished_size_increased(app, tmp_path):
    page = CompressPage()
    page.show()
    pdf_path = str(tmp_path / "original.pdf")
    out_path = str(tmp_path / "compressed.pdf")
    create_test_pdf(pdf_path, pages=1)
    create_test_pdf(out_path, pages=1)

    page.load_pdf_file(pdf_path)

    mock_metrics = {
        "original_size": 1000,
        "compressed_size": 1100,
        "saved_bytes": -100,
        "change_percent": -10.0,
        "is_larger": True,
        "is_same": False,
        "summary_text": "Ukuran bertambah 100 B (+10.0%)",
        "output_path": out_path,
        "page_count": 1,
    }

    page.on_worker_finished(True, "Operasi selesai", mock_metrics)

    assert page.result_card.isVisible() is True
    assert "Ukuran bertambah" in page.savings_badge.text()
    assert page.larger_note_label.isVisible() is True


def test_main_window_navigation_to_compress(app):
    win = MainWindow()

    # Initial page is home
    assert win.content.currentWidget() == win.home_page

    # Navigate via nav button
    win.show_compress()
    assert win.content.currentWidget() == win.compress_page
    assert win.nav_buttons["Compress PDF"].property("active") == "true"

    # Navigate back to home
    win.compress_page.go_back.emit()
    assert win.content.currentWidget() == win.home_page
    assert win.home_button.property("active") == "true"

    # Navigate via Home page feature selection
    win.on_feature_selected("Compress PDF")
    assert win.content.currentWidget() == win.compress_page


def test_compress_page_responsive_resize(app):
    page = CompressPage()
    page.resize(1000, 700)
    app.processEvents()

    # Narrow width should adjust margins
    page.resize(500, 700)
    ev = QResizeEvent(QSize(500, 700), QSize(1000, 700))
    page.resizeEvent(ev)
    assert page.content_layout.contentsMargins().left() == 16
