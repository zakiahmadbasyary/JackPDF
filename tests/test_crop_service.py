import os
import pymupdf as fitz
import pytest

from app.services.crop_service import (
    crop_pdf,
    get_default_output_filename,
    get_default_output_path,
    get_page_info,
)
from app.utils.pdf_geometry import CropMargins, mm_to_points


def create_test_pdf(path: str, pages: int = 3, widths=None, heights=None):
    doc = fitz.open()
    for i in range(pages):
        w = widths[i] if widths and i < len(widths) else 595.0
        h = heights[i] if heights and i < len(heights) else 842.0
        p = doc.new_page(width=w, height=h)
        p.insert_text((50, 50), f"Page {i + 1}")
    doc.save(path)
    doc.close()


def test_default_output_naming():
    src = "C:/docs/My Report.pdf"
    name = get_default_output_filename(src)
    assert name == "My Report_cropped.pdf"

    path = get_default_output_path(src)
    assert path == os.path.abspath("C:/docs/My Report_cropped.pdf")


def test_get_page_info(tmp_path):
    pdf = str(tmp_path / "info_test.pdf")
    create_test_pdf(pdf, pages=2)

    ok, err, w_mm, h_mm, total = get_page_info(pdf, page_num=1)
    assert ok is True
    assert err == ""
    assert total == 2
    # 595.0 points ~ 209.9 mm, 842.0 points ~ 297.0 mm (A4)
    assert pytest.approx(w_mm, 1.0) == 210.0
    assert pytest.approx(h_mm, 1.0) == 297.0


def test_crop_pdf_all_pages(tmp_path):
    src = str(tmp_path / "all_pages_src.pdf")
    dst = str(tmp_path / "all_pages_dst.pdf")
    create_test_pdf(src, pages=3)
    initial_src_size = os.path.getsize(src)

    margins = CropMargins(top_mm=10.0, bottom_mm=10.0, left_mm=15.0, right_mm=15.0)

    ok, msg, data = crop_pdf(src, dst, margins)
    assert ok is True
    assert data["total_cropped"] == 3
    assert data["failed_pages"] == []

    # Source file must NOT be modified
    assert os.path.exists(src)
    assert os.path.getsize(src) == initial_src_size

    # Verify destination PDF
    assert os.path.exists(dst)
    doc = fitz.open(dst)
    assert doc.page_count == 3
    top_pt, bottom_pt, left_pt, right_pt = margins.to_points()
    for page in doc:
        cb = page.cropbox
        assert pytest.approx(cb.x0, 0.1) == left_pt
        assert pytest.approx(cb.y0, 0.1) == top_pt
        assert pytest.approx(cb.x1, 0.1) == 595.0 - right_pt
        assert pytest.approx(cb.y1, 0.1) == 842.0 - bottom_pt
    doc.close()


def test_crop_pdf_specific_pages(tmp_path):
    src = str(tmp_path / "spec_src.pdf")
    dst = str(tmp_path / "spec_dst.pdf")
    create_test_pdf(src, pages=4)

    margins = CropMargins(top_mm=20.0, bottom_mm=20.0, left_mm=20.0, right_mm=20.0)
    # Only crop pages 1 and 3
    ok, msg, data = crop_pdf(src, dst, margins, pages=[1, 3])
    assert ok is True
    assert data["total_cropped"] == 2
    assert data["cropped_pages"] == [1, 3]

    doc = fitz.open(dst)
    assert doc.page_count == 4
    # Page 1 (index 0) is cropped
    assert doc[0].cropbox != doc[0].mediabox
    # Page 2 (index 1) is NOT cropped
    assert doc[1].cropbox == doc[1].mediabox
    # Page 3 (index 2) is cropped
    assert doc[2].cropbox != doc[2].mediabox
    # Page 4 (index 3) is NOT cropped
    assert doc[3].cropbox == doc[3].mediabox
    doc.close()


def test_crop_pdf_source_equals_destination_rejected(tmp_path):
    src = str(tmp_path / "same.pdf")
    create_test_pdf(src, pages=1)

    ok, msg, _ = crop_pdf(src, src, CropMargins(5, 5, 5, 5))
    assert ok is False
    assert "tidak boleh sama" in msg.lower()


def test_crop_pdf_differing_page_sizes_with_failures(tmp_path):
    src = str(tmp_path / "mixed.pdf")
    dst = str(tmp_path / "mixed_out.pdf")
    # Page 1 is large (500x500 pt ~ 176x176 mm)
    # Page 2 is tiny (50x50 pt ~ 17.6x17.6 mm)
    create_test_pdf(src, pages=2, widths=[500.0, 50.0], heights=[500.0, 50.0])

    # Margins 20mm each side -> 40mm total (exceeds 17.6mm for page 2)
    margins = CropMargins(top_mm=20, bottom_mm=20, left_mm=20, right_mm=20)
    ok, msg, data = crop_pdf(src, dst, margins)

    assert ok is True
    assert data["total_cropped"] == 1
    assert data["cropped_pages"] == [1]
    assert data["failed_pages"] == [2]
    assert "dilewati" in msg.lower()


def test_crop_pdf_cancellation(tmp_path):
    src = str(tmp_path / "cancel_test.pdf")
    dst = str(tmp_path / "cancel_out.pdf")
    create_test_pdf(src, pages=5)

    # Cancel immediately
    ok, msg, data = crop_pdf(
        src,
        dst,
        CropMargins(5, 5, 5, 5),
        is_cancelled_callback=lambda: True,
    )

    assert ok is False
    assert data.get("is_cancelled") is True
    assert not os.path.exists(dst)

