"""
crop_service.py - Backend service for JackPDF Crop PDF feature.

Performs page validation, physical margin calculation, CropBox application,
and safe PDF saving without modifying or deleting the source file.
"""

import os
import re
from typing import Callable, Dict, List, Optional, Tuple, Any
import pymupdf as fitz

from app.utils.pdf_geometry import (
    CropMargins,
    calculate_crop_rect,
    points_to_mm,
    validate_crop_margins,
)
from app.utils.validators import validate_pdf_file


def get_default_output_filename(input_path: str) -> str:
    """Generate default output filename: '{stem}_cropped.pdf'."""
    base = os.path.basename(input_path)
    stem, _ = os.path.splitext(base)
    # Sanitize stem
    stem_clean = re.sub(r'[\\/*?:"<>|]', "", stem)
    return f"{stem_clean}_cropped.pdf"


def get_default_output_path(input_path: str) -> str:
    """Generate default output path in the same directory as source."""
    directory = os.path.dirname(os.path.abspath(input_path))
    filename = get_default_output_filename(input_path)
    return os.path.join(directory, filename)


def get_page_info(
    input_path: str,
    page_num: int = 1,
    password: Optional[str] = None,
) -> Tuple[bool, str, float, float, int]:
    """
    Retrieve page dimensions in mm and total page count.
    Returns: (success, error_msg, width_mm, height_mm, total_pages)
    """
    if not os.path.exists(input_path):
        return False, "File tidak ditemukan.", 0.0, 0.0, 0

    try:
        doc = fitz.open(input_path)
        if doc.is_encrypted:
            if not password or not doc.authenticate(password):
                doc.close()
                return False, "Dokumen dilindungi kata sandi.", 0.0, 0.0, 0

        total = doc.page_count
        if total < 1:
            doc.close()
            return False, "Dokumen tidak memiliki halaman.", 0.0, 0.0, 0

        idx = max(0, min(page_num - 1, total - 1))
        page = doc[idx]
        rect = page.rect
        w_mm = points_to_mm(rect.width)
        h_mm = points_to_mm(rect.height)
        doc.close()
        return True, "", w_mm, h_mm, total
    except Exception as e:
        return False, f"Gagal membaca info dokumen: {e}", 0.0, 0.0, 0


def crop_pdf(
    input_path: str,
    output_path: str,
    margins: CropMargins,
    pages: Optional[List[int]] = None,
    password: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    is_cancelled_callback: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Crop selected pages of input PDF by applying CropBox based on physical margins (mm).
    Returns: (success, message, result_data)
    """
    norm_input = os.path.abspath(input_path)
    norm_output = os.path.abspath(output_path)

    # 1. Basic Path & Source Protection Validations
    if not os.path.exists(norm_input):
        return False, f"File sumber tidak ditemukan: '{norm_input}'", None

    if norm_input.lower() == norm_output.lower():
        return False, "Nama file atau folder output tidak boleh sama dengan file sumber.", None

    # Validate input PDF
    is_valid, err_msg, total_pages = validate_pdf_file(norm_input, password=password)
    if not is_valid:
        return False, f"File sumber bukan PDF yang valid: {err_msg}", None

    if total_pages < 1:
        return False, "Dokumen PDF kosong atau tidak memiliki halaman.", None

    # 2. Determine target pages (1-based)
    if pages is None or len(pages) == 0:
        target_pages = list(range(1, total_pages + 1))
    else:
        target_pages = sorted(set(p for p in pages if 1 <= p <= total_pages))

    if not target_pages:
        return False, "Tidak ada halaman valid yang dipilih untuk di-crop.", None

    # Ensure output directory exists
    out_dir = os.path.dirname(norm_output)
    if out_dir and not os.path.exists(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            return False, f"Gagal membuat folder tujuan: {e}", None

    doc = None
    try:
        doc = fitz.open(norm_input)
        if doc.is_encrypted and password:
            doc.authenticate(password)

        total_target = len(target_pages)
        cropped_pages: List[int] = []
        failed_pages: List[int] = []

        for idx, page_num in enumerate(target_pages):
            if is_cancelled_callback and is_cancelled_callback():
                doc.close()
                if os.path.exists(norm_output):
                    try:
                        os.remove(norm_output)
                    except Exception:
                        pass
                return (
                    False,
                    "Proses crop dibatalkan oleh pengguna.",
                    {
                        "is_cancelled": True,
                        "output_path": norm_output,
                        "total_requested": total_target,
                        "total_cropped": len(cropped_pages),
                    },
                )

            if progress_callback:
                progress_callback(
                    idx,
                    total_target,
                    f"Memotong halaman {page_num} ({idx + 1} dari {total_target})...",
                )

            # PyMuPDF page index is 0-based
            page = doc[page_num - 1]
            page_rect = page.rect

            # Validate margins against this specific page's dimensions
            valid, err = validate_crop_margins(page_rect.width, page_rect.height, margins)
            if not valid:
                failed_pages.append(page_num)
                continue

            # Calculate and set crop box
            crop_rect = calculate_crop_rect(page_rect, margins)
            page.set_cropbox(crop_rect)
            cropped_pages.append(page_num)

        if not cropped_pages:
            doc.close()
            return (
                False,
                f"Semua {len(failed_pages)} halaman terpilih gagal di-crop karena margin melebihi ukuran halaman.",
                {
                    "total_requested": total_target,
                    "total_cropped": 0,
                    "failed_pages": failed_pages,
                    "output_path": norm_output,
                },
            )

        if progress_callback:
            progress_callback(total_target, total_target, "Menyimpan file hasil crop...")

        # Save to output file
        doc.save(norm_output, garbage=3, deflate=True)
        doc.close()
        doc = None

        # Verify output file can be opened and has correct page count
        verify_doc = fitz.open(norm_output)
        out_page_count = verify_doc.page_count
        verify_doc.close()

        if out_page_count != total_pages:
            return (
                False,
                f"Integritas file hasil crop tidak sesuai: jumlah halaman {out_page_count} != {total_pages}.",
                None,
            )

        result_data = {
            "input_path": norm_input,
            "output_path": norm_output,
            "total_pages": total_pages,
            "total_requested": total_target,
            "total_cropped": len(cropped_pages),
            "cropped_pages": cropped_pages,
            "failed_pages": failed_pages,
            "margins": margins,
            "is_cancelled": False,
        }

        msg = f"Berhasil memotong {len(cropped_pages)} halaman dokumen."
        if failed_pages:
            msg += f" (Peringatan: {len(failed_pages)} halaman dilewati karena margin terlalu besar)."

        return True, msg, result_data

    except Exception as e:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass
        return False, f"Terjadi kesalahan saat memproses crop: {e}", None

