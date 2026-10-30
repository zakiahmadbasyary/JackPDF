import os
import sys
import pymupdf as fitz
import pytest
from PySide6.QtWidgets import QApplication

from app.services.split_service import (
    split_pdf_by_range,
    split_pdf_each_page,
    split_pdf_fixed_size,
    split_pdf_multi_ranges,
)
from app.ui.pages.split_page import SplitPage
from app.utils.validators import parse_page_range


def create_dummy_pdf(path: str, num_pages: int):
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i + 1} Content")
    doc.save(path)
    doc.close()


def test_split_by_range_continuous(tmp_path):
    src_pdf = str(tmp_path / "sample.pdf")
    out_pdf = str(tmp_path / "extracted_1_3.pdf")
    create_dummy_pdf(src_pdf, 5)

    success, msg, files = split_pdf_by_range(src_pdf, "1-3", out_pdf)
    assert success is True
    assert len(files) == 1
    assert os.path.exists(out_pdf)

    res = fitz.open(out_pdf)
    assert res.page_count == 3
    assert "Page 1 Content" in res[0].get_text()
    assert "Page 2 Content" in res[1].get_text()
    assert "Page 3 Content" in res[2].get_text()
    res.close()


def test_split_by_range_discrete(tmp_path):
    src_pdf = str(tmp_path / "sample.pdf")
    out_pdf = str(tmp_path / "extracted_1_3_5.pdf")
    create_dummy_pdf(src_pdf, 6)

    success, msg, files = split_pdf_by_range(src_pdf, "1,3,5", out_pdf)
    assert success is True
    assert len(files) == 1

    res = fitz.open(out_pdf)
    assert res.page_count == 3
    assert "Page 1 Content" in res[0].get_text()
    assert "Page 3 Content" in res[1].get_text()
    assert "Page 5 Content" in res[2].get_text()
    res.close()


def test_split_each_page(tmp_path):
    src_pdf = str(tmp_path / "sample.pdf")
    out_dir = str(tmp_path / "pages_output")
    create_dummy_pdf(src_pdf, 4)

    success, msg, files = split_pdf_each_page(src_pdf, out_dir)
    assert success is True
    assert len(files) == 4
    for idx, fpath in enumerate(files):
        assert os.path.exists(fpath)
        d = fitz.open(fpath)
        assert d.page_count == 1
        assert f"Page {idx + 1} Content" in d[0].get_text()
        d.close()


def test_split_fixed_size(tmp_path):
    src_pdf = str(tmp_path / "sample.pdf")
    out_dir = str(tmp_path / "parts_output")
    create_dummy_pdf(src_pdf, 5)

    # 5 pages into chunks of 2: part1 (2), part2 (2), part3 (1)
    success, msg, files = split_pdf_fixed_size(src_pdf, out_dir, pages_per_file=2)
    assert success is True
    assert len(files) == 3

    d1 = fitz.open(files[0])
    assert d1.page_count == 2
    d1.close()

    d3 = fitz.open(files[2])
    assert d3.page_count == 1
    d3.close()


def test_parse_page_range_validation():
    # Valid ranges
    ok, pages, err = parse_page_range("1-3, 5, 8-10", 10)
    assert ok is True
    assert pages == [1, 2, 3, 5, 8, 9, 10]

    # Zero rejection
    ok, _, err = parse_page_range("0, 1, 2", 10)
    assert ok is False
    assert "0" in err

    # Reverse range rejection
    ok, _, err = parse_page_range("5-2", 10)
    assert ok is False
    assert "terbalik" in err

    # Out of bounds rejection
    ok, _, err = parse_page_range("1-15", 10)
    assert ok is False
    assert "melebihi" in err

    # Duplicate rejection
    ok, _, err = parse_page_range("1, 2, 2, 3", 10)
    assert ok is False
    assert "duplikat" in err

    # Malformed rejection
    ok, _, err = parse_page_range("1--3", 10)
    assert ok is False

    ok, _, err = parse_page_range("a-b", 10)
    assert ok is False

    ok, _, err = parse_page_range("", 10)
    assert ok is False


def test_split_multi_ranges_merged(tmp_path):
    src_pdf = str(tmp_path / "multi_doc.pdf")
    out_pdf = str(tmp_path / "merged_ranges.pdf")
    create_dummy_pdf(src_pdf, 10)

    # Extract Range 1: 1-3, Range 2: 7-9 into 1 merged PDF
    ranges = [(1, 3), (7, 9)]
    ok, msg, files = split_pdf_multi_ranges(src_pdf, ranges, out_pdf, merge_ranges=True)
    assert ok is True
    assert len(files) == 1
    assert os.path.exists(out_pdf)

    res = fitz.open(out_pdf)
    assert res.page_count == 6  # 3 + 3
    assert "Page 1 Content" in res[0].get_text()
    assert "Page 2 Content" in res[1].get_text()
    assert "Page 3 Content" in res[2].get_text()
    assert "Page 7 Content" in res[3].get_text()
    assert "Page 8 Content" in res[4].get_text()
    assert "Page 9 Content" in res[5].get_text()
    res.close()


def test_split_multi_ranges_separate(tmp_path):
    src_pdf = str(tmp_path / "doc_sep.pdf")
    out_dir = str(tmp_path / "separate_output")
    create_dummy_pdf(src_pdf, 8)

    # Extract Range 1: 2-3, Range 2: 5-6 into separate files
    ranges = [(2, 3), (5, 6)]
    ok, msg, files = split_pdf_multi_ranges(src_pdf, ranges, out_dir, merge_ranges=False)
    assert ok is True
    assert len(files) == 2

    # Part 1: pages 2-3
    d1 = fitz.open(files[0])
    assert d1.page_count == 2
    assert "Page 2 Content" in d1[0].get_text()
    assert "Page 3 Content" in d1[1].get_text()
    d1.close()

    # Part 2: pages 5-6
    d2 = fitz.open(files[1])
    assert d2.page_count == 2
    assert "Page 5 Content" in d2[0].get_text()
    assert "Page 6 Content" in d2[1].get_text()
    d2.close()


def test_split_multi_ranges_validation(tmp_path):
    src_pdf = str(tmp_path / "val_doc.pdf")
    out_pdf = str(tmp_path / "out.pdf")
    create_dummy_pdf(src_pdf, 5)

    # Start > end
    ok, err, _ = split_pdf_multi_ranges(src_pdf, [(4, 2)], out_pdf)
    assert ok is False
    assert "tidak valid" in err

    # Out of bounds
    ok, err, _ = split_pdf_multi_ranges(src_pdf, [(1, 8)], out_pdf)
    assert ok is False
    assert "luar batas" in err


def test_split_page_ui_multi_range_workflow(tmp_path):
    import sys
    from PySide6.QtWidgets import QApplication
    from app.ui.pages.split_page import SplitPage

    app = QApplication.instance() or QApplication(sys.argv)
    page = SplitPage()
    page.show()

    assert not page.info_card.isVisible()
    assert not page.range_card.isVisible()
    assert page.drop_zone.isVisible()
    assert not page.split_btn.isEnabled()

    # Load 10-page dummy PDF
    pdf_path = str(tmp_path / "ui_test.pdf")
    create_dummy_pdf(pdf_path, 10)
    page.load_pdf_file(pdf_path)

    assert page.info_card.isVisible()
    assert page.range_card.isVisible()
    assert not page.drop_zone.isVisible()
    assert len(page.range_rows) == 1
    assert page.range_rows[0].get_range() == (1, 3)
    assert page.merge_checkbox.isChecked()
    assert page.split_btn.isEnabled()

    # Add second range row
    page.add_range_btn.click()
    assert len(page.range_rows) == 2
    # Smart default: after 3 is 4, ends at 6
    assert page.range_rows[1].get_range() == (4, 6)
    assert page.merge_checkbox.isVisible()

    # Add third range row
    page.add_range_btn.click()
    assert len(page.range_rows) == 3
    assert page.range_rows[2].get_range() == (7, 9)

    # Test deleting middle row
    middle_row = page.range_rows[1]
    middle_row.del_btn.click()
    assert len(page.range_rows) == 2
    assert page.range_rows[0].title_label.text() == "Rentang 1:"
    assert page.range_rows[1].title_label.text() == "Rentang 2:"

    # Test invalid range disables split button
    page.range_rows[0].set_range(5, 2)  # start > end
    assert not page.split_btn.isEnabled()

    # Fix range
    page.range_rows[0].set_range(1, 3)
    assert page.split_btn.isEnabled()

    # Reset form
    page.reset_btn.click()
    assert not page.info_card.isVisible()
    assert not page.range_card.isVisible()
    assert page.drop_zone.isVisible()
    assert not page.split_btn.isEnabled()
    assert len(page.range_rows) == 0


def test_split_page_preview_panel_functionality(tmp_path):
    app = QApplication.instance() or QApplication(sys.argv)
    page = SplitPage()
    page.resize(1000, 700)
    page.show()

    assert hasattr(page, "preview_panel")
    assert hasattr(page, "toggle_preview_btn")
    assert not page.preview_panel.isVisible()
    assert not page.toggle_preview_btn.isVisible()

    pdf_path = str(tmp_path / "preview_test.pdf")
    create_dummy_pdf(pdf_path, 8)

    # Load PDF: preview should load page 0 and become visible
    page.load_pdf_file(pdf_path)
    assert page.preview_panel.isVisible()
    assert page.toggle_preview_btn.isVisible()
    assert page.preview_panel.current_path == os.path.abspath(pdf_path)
    assert page.preview_panel.current_page == 0
    assert page.preview_panel.total_pages == 8
    assert page.preview_panel.page_badge.text() == "Hal 1/8"
    assert "Estimasi Hasil:" in page.preview_panel.summary_badge.text()

    # Test navigating preview directly with next_page
    page.preview_panel.next_page()
    assert page.preview_panel.current_page == 1
    assert page.preview_panel.page_badge.text() == "Hal 2/8"

    # Test interactive page jump from range row: adjust from_spin to 5
    page.range_rows[0].from_spin.setValue(5)
    assert page.preview_panel.current_page == 4  # 0-indexed page 4 is Hal 5
    assert page.preview_panel.page_badge.text() == "Hal 5/8"

    # Test toggle preview button
    page.toggle_preview_btn.click()
    assert not page.preview_panel.isVisible()
    assert page.toggle_preview_btn.text() == "Tampilkan Pratinjau"

    page.toggle_preview_btn.click()
    assert page.preview_panel.isVisible()
    assert page.toggle_preview_btn.text() == "Sembunyikan Pratinjau"

    # Test reset clears and hides preview
    page.reset_btn.click()
    assert not page.preview_panel.isVisible()
    assert not page.toggle_preview_btn.isVisible()
    assert page.preview_panel.current_path is None
