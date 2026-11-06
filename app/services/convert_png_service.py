import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
import pymupdf as fitz

from app.utils.validators import validate_pdf_file


def format_page_selection(pages: List[int]) -> str:
    """
    Format a list of 1-based page numbers into a clean, compact string.
    Example: [1, 2, 3, 5, 7, 8, 9] -> '1-3, 5, 7-9'.
    """
    if not pages:
        return ""
    sorted_pages = sorted(set(pages))
    ranges = []
    start = sorted_pages[0]
    prev = start
    for p in sorted_pages[1:]:
        if p == prev + 1:
            prev = p
        else:
            ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
            start = p
            prev = p
    ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
    return ", ".join(ranges)


def parse_page_selection(value: str, total_pages: int) -> Tuple[bool, List[int], str]:
    """
    Parse a page range string (1-based) into a sorted unique list of page numbers.
    Validates:
      - Empty strings
      - Disallowed characters (only digits, spaces, commas, hyphens allowed)
      - Empty comma tokens (e.g. '1,,2')
      - Reverse ranges (e.g. '5-2')
      - Out of bounds (<= 0 or > total_pages)
      - Non-numeric tokens
    Returns: (is_valid, list_of_pages, error_message)
    """
    if not value or not value.strip():
        return False, [], "Input nomor halaman tidak boleh kosong."

    clean = value.strip()
    if not re.match(r"^[\d\s,-]+$", clean):
        return (
            False,
            [],
            "Format tidak valid. Gunakan angka, koma, dan tanda hubung (-). Contoh: 1, 3, 6-8, 12",
        )

    tokens = clean.split(",")
    result_pages = set()

    for raw in tokens:
        token = raw.strip()
        if not token:
            return False, [], "Format tidak valid (ditemukan koma kosong atau berlebih)."

        if "-" in token:
            sub = token.split("-")
            if len(sub) != 2:
                return False, [], f"Format rentang '{token}' tidak valid."
            start_str, end_str = sub[0].strip(), sub[1].strip()
            if not start_str.isdigit() or not end_str.isdigit():
                return False, [], f"Format rentang '{token}' harus berupa angka."
            s, e = int(start_str), int(end_str)
            if s <= 0 or e <= 0:
                return False, [], "Nomor halaman harus dimulai dari 1."
            if s > e:
                return (
                    False,
                    [],
                    f"Rentang terbalik '{token}' tidak valid (halaman awal harus <= halaman akhir).",
                )
            if e > total_pages:
                return (
                    False,
                    [],
                    f"Halaman {e} melebihi jumlah total halaman PDF ({total_pages}).",
                )
            for p in range(s, e + 1):
                result_pages.add(p)
        else:
            if not token.isdigit():
                return False, [], f"Nilai '{token}' bukan angka yang valid."
            p = int(token)
            if p <= 0:
                return False, [], "Nomor halaman harus dimulai dari 1."
            if p > total_pages:
                return (
                    False,
                    [],
                    f"Halaman {p} melebihi jumlah total halaman PDF ({total_pages}).",
                )
            result_pages.add(p)

    if not result_pages:
        return False, [], "Pilih minimal satu halaman untuk dikonversi."

    return True, sorted(result_pages), ""


def get_default_output_dir(pdf_path: str) -> str:
    """Return the default output directory path next to the source PDF."""
    dir_name = os.path.dirname(os.path.abspath(pdf_path))
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    # Clean base_name of trailing spaces or dots
    clean_base = base_name.strip(". ")
    return os.path.join(dir_name, f"{clean_base}_png")


def get_output_filename(base_name: str, page_num: int, total_pages: int) -> str:
    """
    Format output PNG filename using the original 1-based page number and dynamic zero-padding.
    Example: 'document_page-001.png'.
    """
    clean_base = base_name.strip(". ")
    pad_width = max(3, len(str(total_pages)))
    return f"{clean_base}_page-{page_num:0{pad_width}d}.png"


def convert_pdf_to_png(
    input_path: str,
    output_dir: str,
    pages: Optional[List[int]] = None,
    dpi: int = 200,
    color_mode: str = "rgb",
    password: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    is_cancelled_callback: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Convert selected PDF pages to individual PNG image files.

    Parameters:
        input_path: Absolute path to the source PDF file.
        output_dir: Target directory where PNG images will be saved.
        pages: List of 1-based page numbers to convert. If None, converts all pages.
        dpi: Target DPI resolution (72 - 600, default: 200).
        color_mode: 'rgb' or 'grayscale' (default: 'rgb').
        password: Password if PDF is encrypted.
        progress_callback: Callback(current_completed, total_requested, status_message).
        is_cancelled_callback: Function returning True if user requested cancellation.

    Returns:
        (success: bool, message: str, result_data: dict)
    """
    if not input_path or not os.path.exists(input_path):
        return False, "Silakan pilih file PDF terlebih dahulu.", {}

    if not output_dir or not output_dir.strip():
        return False, "Folder tujuan penyimpanan belum ditentukan.", {}

    # Validate input PDF
    is_valid, err_msg, total_pages = validate_pdf_file(input_path, password=password)
    if not is_valid:
        return False, err_msg, {}

    if total_pages < 1:
        return False, "File PDF tidak memiliki halaman yang dapat dikonversi.", {}

    # Validate DPI range
    if not isinstance(dpi, int) or dpi < 72 or dpi > 600:
        return False, "DPI harus berupa angka antara 72 dan 600.", {}

    # Validate and normalize Color mode
    mode_lower = color_mode.lower().strip()
    if mode_lower not in ("rgb", "grayscale"):
        return False, f"Mode warna '{color_mode}' tidak didukung. Pilih 'RGB' atau 'Grayscale'.", {}

    colorspace = fitz.csGRAY if mode_lower == "grayscale" else fitz.csRGB

    # Determine pages to convert
    if pages is None:
        target_pages = list(range(1, total_pages + 1))
    else:
        target_pages = sorted(set(pages))
        for p in target_pages:
            if p < 1 or p > total_pages:
                return (
                    False,
                    f"Nomor halaman {p} di luar rentang halaman PDF (1-{total_pages}).",
                    {},
                )

    if not target_pages:
        return False, "Pilih minimal satu halaman untuk dikonversi.", {}

    # Ensure output directory exists
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        return False, f"Folder tujuan tidak dapat diakses atau dibuat: {str(e)}", {}

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    total_to_convert = len(target_pages)
    generated_files: List[str] = []
    failed_pages: List[int] = []
    was_cancelled = False

    doc = None
    try:
        doc = fitz.open(input_path)
        if doc.is_encrypted:
            rc = doc.authenticate(password or "")
            if rc == 0:
                return (
                    False,
                    "PDF ini dilindungi password. Masukkan password atau pilih file lain.",
                    {},
                )

        for idx, page_num in enumerate(target_pages):
            # Check for user cancellation
            if is_cancelled_callback and is_cancelled_callback():
                was_cancelled = True
                break

            if progress_callback:
                progress_callback(
                    idx,
                    total_to_convert,
                    f"Memproses halaman {idx + 1} dari {total_to_convert} (Halaman {page_num})...",
                )

            page_index = page_num - 1
            out_filename = get_output_filename(base_name, page_num, total_pages)
            out_path = os.path.join(output_dir, out_filename)

            try:
                page = doc[page_index]
                # Render page to pixmap with anti-aliasing and white background
                pix = page.get_pixmap(dpi=dpi, colorspace=colorspace, alpha=False)
                pix.save(out_path)
                generated_files.append(out_path)
            except Exception:
                failed_pages.append(page_num)

        if progress_callback and not was_cancelled:
            progress_callback(total_to_convert, total_to_convert, "Selesai memproses seluruh halaman.")

    except Exception as e:
        return False, f"Proses konversi gagal: {str(e)}. File PDF asli tetap aman.", {}
    finally:
        if doc:
            try:
                doc.close()
            except Exception:
                pass

    result_data = {
        "generated_files": generated_files,
        "failed_pages": failed_pages,
        "total_requested": total_to_convert,
        "total_success": len(generated_files),
        "output_dir": output_dir,
        "dpi": dpi,
        "color_mode": mode_lower,
        "is_cancelled": was_cancelled,
    }

    if was_cancelled:
        return (
            True,
            f"Proses konversi dibatalkan. {len(generated_files)} dari {total_to_convert} halaman berhasil disimpan.",
            result_data,
        )

    if failed_pages:
        failed_str = ", ".join(map(str, failed_pages))
        if generated_files:
            return (
                False,
                f"Konversi selesai sebagian: {len(generated_files)} berhasil, {len(failed_pages)} gagal (Halaman: {failed_str}).",
                result_data,
            )
        else:
            return False, f"Seluruh halaman gagal dikonversi (Halaman: {failed_str}).", result_data

    return (
        True,
        f"Berhasil mengonversi {len(generated_files)} halaman PDF ke file gambar PNG.",
        result_data,
    )

