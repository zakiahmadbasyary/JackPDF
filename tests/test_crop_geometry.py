import pytest
import pymupdf as fitz
from PySide6.QtCore import QRectF

from app.utils.pdf_geometry import (
    CropMargins,
    calculate_crop_rect,
    display_rect_to_pdf_rect,
    margins_from_crop_rect,
    mm_to_points,
    pdf_rect_to_display_rect,
    points_to_mm,
    validate_crop_margins,
)


def test_mm_and_points_conversion():
    # 25.4 mm is exactly 1 inch = 72 points
    assert pytest.approx(mm_to_points(25.4), 0.001) == 72.0
    assert pytest.approx(points_to_mm(72.0), 0.001) == 25.4

    # Round trip
    val_mm = 15.5
    assert pytest.approx(points_to_mm(mm_to_points(val_mm)), 0.001) == val_mm


def test_calculate_crop_rect():
    page_box = fitz.Rect(0, 0, 595.0, 842.0)
    margins = CropMargins(top_mm=10.0, bottom_mm=15.0, left_mm=20.0, right_mm=25.0)

    crop_rect = calculate_crop_rect(page_box, margins)

    top_pt, bottom_pt, left_pt, right_pt = margins.to_points()
    assert pytest.approx(crop_rect.x0, 0.01) == left_pt
    assert pytest.approx(crop_rect.y0, 0.01) == top_pt
    assert pytest.approx(crop_rect.x1, 0.01) == 595.0 - right_pt
    assert pytest.approx(crop_rect.y1, 0.01) == 842.0 - bottom_pt


def test_margins_from_crop_rect():
    page_box = fitz.Rect(0, 0, 500, 500)
    crop_rect = fitz.Rect(50, 60, 420, 410)

    margins = margins_from_crop_rect(page_box, crop_rect)
    assert pytest.approx(margins.left_mm, 0.1) == points_to_mm(50)
    assert pytest.approx(margins.top_mm, 0.1) == points_to_mm(60)
    assert pytest.approx(margins.right_mm, 0.1) == points_to_mm(80)
    assert pytest.approx(margins.bottom_mm, 0.1) == points_to_mm(90)


def test_validate_crop_margins():
    # A4: ~210 mm x ~297 mm
    w_pt, h_pt = 595.0, 842.0

    # Valid margins
    valid, msg = validate_crop_margins(w_pt, h_pt, CropMargins(10, 10, 10, 10))
    assert valid is True
    assert msg == ""

    # Negative margin
    valid, msg = validate_crop_margins(w_pt, h_pt, CropMargins(-1, 0, 0, 0))
    assert valid is False
    assert "negatif" in msg.lower()

    # Excessive horizontal margins (e.g. 150mm + 150mm = 300mm > 210mm)
    valid, msg = validate_crop_margins(w_pt, h_pt, CropMargins(0, 0, 150, 150))
    assert valid is False
    assert "horizontal" in msg.lower()

    # Excessive vertical margins
    valid, msg = validate_crop_margins(w_pt, h_pt, CropMargins(200, 200, 0, 0))
    assert valid is False
    assert "vertikal" in msg.lower()


def test_display_and_pdf_rect_mapping():
    page_box = fitz.Rect(0, 0, 600, 800)
    canvas_rect = QRectF(50, 50, 300, 400)  # scale is exactly 0.5

    crop_rect = fitz.Rect(100, 200, 500, 600)
    disp = pdf_rect_to_display_rect(crop_rect, page_box, canvas_rect)

    assert pytest.approx(disp.left(), 0.1) == 50 + 100 * 0.5  # 100
    assert pytest.approx(disp.top(), 0.1) == 50 + 200 * 0.5   # 150
    assert pytest.approx(disp.width(), 0.1) == 400 * 0.5      # 200
    assert pytest.approx(disp.height(), 0.1) == 400 * 0.5     # 200

    # Map back to PDF rect
    reconstructed = display_rect_to_pdf_rect(disp, page_box, canvas_rect)
    assert pytest.approx(reconstructed.x0, 0.1) == crop_rect.x0
    assert pytest.approx(reconstructed.y0, 0.1) == crop_rect.y0
    assert pytest.approx(reconstructed.x1, 0.1) == crop_rect.x1
    assert pytest.approx(reconstructed.y1, 0.1) == crop_rect.y1

