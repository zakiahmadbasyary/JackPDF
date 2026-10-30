import os
import sys
import pymupdf as fitz
import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QApplication, QPushButton

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.ui.pages.merge_page import MergePage, natural_sort_key


def create_test_pdf(path: str, pages: int = 1):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i + 1}")
    doc.save(path)
    doc.close()


@pytest.fixture
def app():
    app_instance = QApplication.instance()
    if app_instance is None:
        app_instance = QApplication(sys.argv)
    return app_instance


def test_merge_page_drag_reordering(app, tmp_path):
    page = MergePage()

    pdf1 = str(tmp_path / "file_a.pdf")
    pdf2 = str(tmp_path / "file_b.pdf")
    pdf3 = str(tmp_path / "file_c.pdf")

    create_test_pdf(pdf1, 1)
    create_test_pdf(pdf2, 2)
    create_test_pdf(pdf3, 3)

    page.add_files([pdf1, pdf2, pdf3])
    assert len(page.file_list) == 3
    assert [f["name"] for f in page.file_list] == ["file_a.pdf", "file_b.pdf", "file_c.pdf"]
    assert page.table.rowCount() == 3

    # Test drag row 2 (file_c) to top (target 0)
    page.on_rows_reordered([2], 0)
    assert [f["name"] for f in page.file_list] == ["file_c.pdf", "file_a.pdf", "file_b.pdf"]
    assert page.table.item(0, 0).text() == "⋮  1"
    assert page.table.item(0, 1).text() == "file_c.pdf"

    # Test drag row 0 (file_c) to end (target 3)
    page.on_rows_reordered([0], 3)
    assert [f["name"] for f in page.file_list] == ["file_a.pdf", "file_b.pdf", "file_c.pdf"]

    # Test multi-row drag: move rows [1, 2] (b and c) to top (target 0)
    page.on_rows_reordered([1, 2], 0)
    assert [f["name"] for f in page.file_list] == ["file_b.pdf", "file_c.pdf", "file_a.pdf"]


def test_merge_page_direct_drop_insert(app, tmp_path):
    page = MergePage()

    pdf1 = str(tmp_path / "doc1.pdf")
    pdf2 = str(tmp_path / "doc2.pdf")
    pdf_insert = str(tmp_path / "doc_inserted.pdf")

    create_test_pdf(pdf1, 1)
    create_test_pdf(pdf2, 1)
    create_test_pdf(pdf_insert, 1)

    page.add_files([pdf1, pdf2])
    assert len(page.file_list) == 2

    # Drop insert right between doc1 and doc2 (target_row=1)
    page.add_files([pdf_insert], target_row=1)
    assert len(page.file_list) == 3
    assert [f["name"] for f in page.file_list] == ["doc1.pdf", "doc_inserted.pdf", "doc2.pdf"]


def test_merge_page_sorting_and_actions(app, tmp_path):
    page = MergePage()

    pdf_part2 = str(tmp_path / "part_2.pdf")
    pdf_part10 = str(tmp_path / "part_10.pdf")
    pdf_part1 = str(tmp_path / "part_1.pdf")

    create_test_pdf(pdf_part2, 2)
    create_test_pdf(pdf_part10, 10)
    create_test_pdf(pdf_part1, 1)

    page.add_files([pdf_part2, pdf_part10, pdf_part1])

    # Verify action column only has delete button (no open/buka action)
    cell_widget = page.table.cellWidget(0, 4)
    assert cell_widget is not None
    buttons = cell_widget.findChildren(QPushButton)
    assert len(buttons) == 1
    assert buttons[0].text() == "Hapus"

    # Test Natural Sort A-Z: part_1, part_2, part_10
    page.sort_by_name(reverse=False)
    assert [f["name"] for f in page.file_list] == ["part_1.pdf", "part_2.pdf", "part_10.pdf"]

    # Test Natural Sort Z-A: part_10, part_2, part_1
    page.sort_by_name(reverse=True)
    assert [f["name"] for f in page.file_list] == ["part_10.pdf", "part_2.pdf", "part_1.pdf"]

    # Test Sort by Pages (Ascending)
    page.sort_by_pages(reverse=False)
    assert [f["pages"] for f in page.file_list] == [1, 2, 10]

    # Test Reverse Order
    page.reverse_order()
    assert [f["pages"] for f in page.file_list] == [10, 2, 1]

    # Test Delete at Row
    page.remove_at_row(1)
    assert len(page.file_list) == 2
    assert [f["pages"] for f in page.file_list] == [10, 1]

    # Test Move Up button
    page.table.selectRow(1)
    page.move_up()
    assert [f["pages"] for f in page.file_list] == [1, 10]

    # Test Move Down button
    page.table.selectRow(0)
    page.move_down()
    assert [f["pages"] for f in page.file_list] == [10, 1]


def test_merge_page_responsiveness(app):
    page = MergePage()

    # Small size (< 640px)
    page.resizeEvent(QResizeEvent(QSize(500, 600), QSize(800, 600)))
    assert page.add_btn.text() == "+ Tambah"
    assert page.up_btn.text() == "↑"
    assert page.down_btn.text() == "↓"
    assert page.del_btn.text() == "Hapus"

    # Standard size (>= 640px)
    page.resizeEvent(QResizeEvent(QSize(800, 600), QSize(500, 600)))
    assert page.add_btn.text() == "+ Tambah PDF"
    assert page.up_btn.text() == "↑ Naik"
    assert page.down_btn.text() == "↓ Turun"
    assert page.del_btn.text() == "Hapus Pilihan"


def test_natural_sort_key():
    assert natural_sort_key("File 2.pdf") < natural_sort_key("File 10.pdf")
    assert natural_sort_key("Chapter 1") < natural_sort_key("Chapter 2") < natural_sort_key("Chapter 20")


def test_merge_table_styling_and_row_persistence(app, tmp_path):
    page = MergePage()
    assert not page.table.verticalHeader().isVisible()
    assert page.table.verticalHeader().defaultSectionSize() == 40

    pdf1 = str(tmp_path / "doc1.pdf")
    pdf2 = str(tmp_path / "doc2.pdf")
    create_test_pdf(pdf1, 1)
    create_test_pdf(pdf2, 2)
    page.add_files([pdf1, pdf2])

    # Reorder
    page.on_rows_reordered([1], 0)

    # Verify no row is blank or lost
    for r in range(page.table.rowCount()):
        for c in range(4):
            item = page.table.item(r, c)
            assert item is not None
            assert len(item.text().strip()) > 0
        action_widget = page.table.cellWidget(r, 4)
        assert action_widget is not None
        assert action_widget.findChild(QPushButton) is not None

    # Test remove by path
    page.remove_by_path(pdf1)
    assert len(page.file_list) == 1
    assert page.file_list[0]["path"] == pdf2


def test_pdf_preview_panel_functionality(app, tmp_path):
    page = MergePage()
    page.resize(900, 600)
    page.show()
    assert hasattr(page, "preview_panel")
    assert hasattr(page, "toggle_preview_btn")
    assert page.preview_panel.empty_widget.isVisible()
    assert not page.preview_panel.image_label.isVisible()

    pdf_multi = str(tmp_path / "multi.pdf")
    pdf_single = str(tmp_path / "single.pdf")
    create_test_pdf(pdf_multi, 3)
    create_test_pdf(pdf_single, 1)

    # Add files: first row should auto-select and render preview
    page.add_files([pdf_multi, pdf_single])
    assert page.preview_panel.current_path == pdf_multi
    assert page.preview_panel.current_page == 0
    assert page.preview_panel.total_pages == 3
    assert page.preview_panel.image_label.isVisible()
    assert page.preview_panel.image_label.pixmap() is not None
    assert page.preview_panel.page_badge.text() == "Hal 1/3"
    assert page.preview_panel.nav_widget.isVisible()
    assert not page.preview_panel.prev_btn.isEnabled()
    assert page.preview_panel.next_btn.isEnabled()

    # Next page navigation
    page.preview_panel.next_page()
    assert page.preview_panel.current_page == 1
    assert page.preview_panel.page_badge.text() == "Hal 2/3"
    assert page.preview_panel.prev_btn.isEnabled()
    assert page.preview_panel.next_btn.isEnabled()

    # Next page to last page
    page.preview_panel.next_page()
    assert page.preview_panel.current_page == 2
    assert page.preview_panel.page_badge.text() == "Hal 3/3"
    assert page.preview_panel.prev_btn.isEnabled()
    assert not page.preview_panel.next_btn.isEnabled()

    # Previous page navigation
    page.preview_panel.prev_page()
    assert page.preview_panel.current_page == 1

    # Select second row (single page PDF)
    page.table.selectRow(1)
    assert page.preview_panel.current_path == pdf_single
    assert page.preview_panel.current_page == 0
    assert page.preview_panel.total_pages == 1
    assert page.preview_panel.page_badge.text() == "Hal 1/1"
    assert not page.preview_panel.nav_widget.isVisible()

    # Test toggle preview panel
    assert page.preview_panel.isVisible()
    page.toggle_preview_btn.click()
    assert not page.preview_panel.isVisible()
    assert page.toggle_preview_btn.text() == "Lihat Pratinjau"
    page.toggle_preview_btn.click()
    assert page.preview_panel.isVisible()
    assert page.toggle_preview_btn.text() == "Sembunyikan Pratinjau"

    # Test clear all resets preview
    page.clear_all()
    assert page.preview_panel.current_path is None
    assert page.preview_panel.empty_widget.isVisible()
    assert not page.preview_panel.image_label.isVisible()
    assert page.preview_panel.page_badge.text() == "—"
