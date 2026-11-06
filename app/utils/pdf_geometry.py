"""
pdf_geometry.py - PDF Coordinate and Geometry Utilities for JackPDF Crop Feature.

Handles conversion between physical millimeters (mm) and PDF points (pt),
margin validation, and screen preview <-> PDF page coordinate mappings.
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import pymupdf as fitz
from PySide6.QtCore import QPointF, QRectF

POINTS_PER_INCH = 72.0
MM_PER_INCH = 25.4
MM_TO_POINTS = POINTS_PER_INCH / MM_PER_INCH      # ~2.83464567 pt/mm
POINTS_TO_MM = MM_PER_INCH / POINTS_PER_INCH      # ~0.35277778 mm/pt


def mm_to_points(mm: float) -> float:
    """Convert millimeters to PDF points."""
    return float(mm) * MM_TO_POINTS


def points_to_mm(points: float) -> float:
    """Convert PDF points to millimeters."""
    return float(points) * POINTS_TO_MM


@dataclass
class CropMargins:
    """
    Physical crop margins in millimeters (mm) applied from the edges of a PDF page.
    """
    top_mm: float = 0.0
    bottom_mm: float = 0.0
    left_mm: float = 0.0
    right_mm: float = 0.0

    def to_points(self) -> Tuple[float, float, float, float]:
        """Return (top_pt, bottom_pt, left_pt, right_pt)."""
        return (
            mm_to_points(self.top_mm),
            mm_to_points(self.bottom_mm),
            mm_to_points(self.left_mm),
            mm_to_points(self.right_mm),
        )

    def is_zero(self, tolerance_mm: float = 0.05) -> bool:
        """Return True if all margins are virtually zero."""
        return (
            abs(self.top_mm) < tolerance_mm
            and abs(self.bottom_mm) < tolerance_mm
            and abs(self.left_mm) < tolerance_mm
            and abs(self.right_mm) < tolerance_mm
        )

    def round_values(self, decimals: int = 1) -> "CropMargins":
        """Return a new CropMargins with rounded numbers."""
        return CropMargins(
            top_mm=round(self.top_mm, decimals),
            bottom_mm=round(self.bottom_mm, decimals),
            left_mm=round(self.left_mm, decimals),
            right_mm=round(self.right_mm, decimals),
        )


def calculate_crop_rect(page_box: fitz.Rect, margins: CropMargins) -> fitz.Rect:
    """
    Calculate the resulting fitz.Rect (in PDF points) from page boundaries and margins.
    """
    top_pt, bottom_pt, left_pt, right_pt = margins.to_points()
    x0 = page_box.x0 + left_pt
    y0 = page_box.y0 + top_pt
    x1 = page_box.x1 - right_pt
    y1 = page_box.y1 - bottom_pt
    return fitz.Rect(x0, y0, x1, y1)


def margins_from_crop_rect(page_box: fitz.Rect, crop_rect: fitz.Rect) -> CropMargins:
    """
    Derive physical margins (in mm) from page boundaries and an inner crop rectangle.
    """
    left_pt = max(0.0, crop_rect.x0 - page_box.x0)
    top_pt = max(0.0, crop_rect.y0 - page_box.y0)
    right_pt = max(0.0, page_box.x1 - crop_rect.x1)
    bottom_pt = max(0.0, page_box.y1 - crop_rect.y1)

    return CropMargins(
        top_mm=points_to_mm(top_pt),
        bottom_mm=points_to_mm(bottom_pt),
        left_mm=points_to_mm(left_pt),
        right_mm=points_to_mm(right_pt),
    )


def validate_crop_margins(
    page_width_pt: float,
    page_height_pt: float,
    margins: CropMargins,
    min_size_mm: float = 5.0,
) -> Tuple[bool, str]:
    """
    Validate that margins are non-negative and leave at least min_size_mm
    of visible content in both dimensions.
    Returns: (is_valid, error_message)
    """
    if (
        margins.top_mm < 0
        or margins.bottom_mm < 0
        or margins.left_mm < 0
        or margins.right_mm < 0
    ):
        return False, "Nilai margin tidak boleh negatif."

    top_pt, bottom_pt, left_pt, right_pt = margins.to_points()
    min_size_pt = mm_to_points(min_size_mm)

    rem_width_pt = page_width_pt - (left_pt + right_pt)
    if rem_width_pt < min_size_pt:
        return (
            False,
            f"Margin horizontal terlalu besar. Sisa lebar {points_to_mm(rem_width_pt):.1f} mm "
            f"(minimal {min_size_mm:.1f} mm).",
        )

    rem_height_pt = page_height_pt - (top_pt + bottom_pt)
    if rem_height_pt < min_size_pt:
        return (
            False,
            f"Margin vertikal terlalu besar. Sisa tinggi {points_to_mm(rem_height_pt):.1f} mm "
            f"(minimal {min_size_mm:.1f} mm).",
        )

    return True, ""


def pdf_rect_to_display_rect(
    crop_rect: fitz.Rect,
    page_box: fitz.Rect,
    canvas_rect: QRectF,
) -> QRectF:
    """
    Map a PDF point crop rectangle into the canvas widget's pixel coordinate space.
    """
    page_w = page_box.width
    page_h = page_box.height
    if page_w <= 0 or page_h <= 0:
        return QRectF()

    scale_x = canvas_rect.width() / page_w
    scale_y = canvas_rect.height() / page_h

    # Relativize to page_box origin
    rel_x0 = crop_rect.x0 - page_box.x0
    rel_y0 = crop_rect.y0 - page_box.y0
    rel_x1 = crop_rect.x1 - page_box.x0
    rel_y1 = crop_rect.y1 - page_box.y0

    disp_x = canvas_rect.left() + rel_x0 * scale_x
    disp_y = canvas_rect.top() + rel_y0 * scale_y
    disp_w = (rel_x1 - rel_x0) * scale_x
    disp_h = (rel_y1 - rel_y0) * scale_y

    return QRectF(disp_x, disp_y, max(1.0, disp_w), max(1.0, disp_h))


def display_rect_to_pdf_rect(
    disp_rect: QRectF,
    page_box: fitz.Rect,
    canvas_rect: QRectF,
) -> fitz.Rect:
    """
    Map a canvas pixel crop rectangle back into PDF point coordinates,
    clamped within page_box.
    """
    if canvas_rect.width() <= 0 or canvas_rect.height() <= 0:
        return fitz.Rect(page_box)

    scale_x = page_box.width / canvas_rect.width()
    scale_y = page_box.height / canvas_rect.height()

    rel_disp_x0 = disp_rect.left() - canvas_rect.left()
    rel_disp_y0 = disp_rect.top() - canvas_rect.top()
    rel_disp_x1 = disp_rect.right() - canvas_rect.left()
    rel_disp_y1 = disp_rect.bottom() - canvas_rect.top()

    pdf_x0 = page_box.x0 + rel_disp_x0 * scale_x
    pdf_y0 = page_box.y0 + rel_disp_y0 * scale_y
    pdf_x1 = page_box.x0 + rel_disp_x1 * scale_x
    pdf_y1 = page_box.y0 + rel_disp_y1 * scale_y

    # Clamp strictly within page_box
    clamped_x0 = max(page_box.x0, min(pdf_x0, page_box.x1))
    clamped_y0 = max(page_box.y0, min(pdf_y0, page_box.y1))
    clamped_x1 = max(clamped_x0, min(pdf_x1, page_box.x1))
    clamped_y1 = max(clamped_y0, min(pdf_y1, page_box.y1))

    return fitz.Rect(clamped_x0, clamped_y0, clamped_x1, clamped_y1)

