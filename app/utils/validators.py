import os
import re
from typing import Tuple, List, Optional
import pymupdf as fitz


def validate_pdf_file(file_path: str, password: Optional[str] = None) -> Tuple[bool, str, int]:
    """
    Validate that a file exists, has .pdf extension, can be opened,
    authenticates if password protected, and has at least 1 page.
    Returns: (is_valid, error_message, page_count)
    """
    if not file_path or not os.path.exists(file_path):
        return False, "File tidak ditemukan.", 0

    if not file_path.lower().endswith(".pdf"):
        return False, "File yang dipilih bukan PDF yang valid.", 0

    try:
        if os.path.getsize(file_path) == 0:
            return False, "File PDF kosong atau tidak dapat diakses.", 0
    except Exception:
        return False, "File PDF tidak dapat diakses.", 0

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return False, "File PDF rusak atau tidak dapat dibaca.", 0

    try:
        if doc.is_encrypted:
            if password is not None:
                rc = doc.authenticate(password)
                if rc == 0:
                    doc.close()
                    return False, "Password PDF salah atau diperlukan.", 0
            else:
                doc.close()
                return False, "File PDF dilindungi password (terenkripsi).", 0

        page_count = doc.page_count
        doc.close()

        if page_count < 1:
            return False, "File PDF tidak memiliki halaman.", 0

        return True, "", page_count
    except Exception as e:
        try:
            doc.close()
        except Exception:
            pass
        return False, "Gagal memverifikasi isi file PDF.", 0


def check_pdf_signatures(file_path: str, password: Optional[str] = None) -> bool:
    """
    Check if a PDF file contains digital signatures.
    Returns True if signatures or signature form fields exist, else False.
    """
    if not file_path or not os.path.exists(file_path):
        return False
    doc = None
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted and password:
            doc.authenticate(password)
        sigflags = doc.get_sigflags()
        if sigflags != -1 and (sigflags & fitz.SigFlag_SignaturesExist):
            doc.close()
            return True
        for page in doc:
            for widget in page.widgets():
                if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                    doc.close()
                    return True
        doc.close()
        return False
    except Exception:
        if doc:
            try:
                doc.close()
            except Exception:
                pass
        return False


def validate_output_filename(filename: str) -> Tuple[bool, str]:
    """
    Validate that an output filename is safe and valid on Windows / common filesystems.
    """
    if not filename or not filename.strip():
        return False, "Nama file tidak boleh kosong."

    clean_name = filename.strip()
    forbidden_chars = r'[<>:"/\\|?*]'
    if re.search(forbidden_chars, clean_name):
        return False, 'Nama file tidak boleh mengandung karakter berikut: < > : " / \\ | ? *'

    base, _ = os.path.splitext(clean_name)
    reserved_names = {
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
        "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    if base.strip().upper() in reserved_names:
        return False, f"Nama file '{base}' adalah nama yang dicadangkan oleh sistem operasi."

    if clean_name.endswith(".") or clean_name.endswith(" "):
        return False, "Nama file tidak boleh diakhiri titik atau spasi."

    return True, ""


def parse_page_range(range_str: str, max_pages: int) -> Tuple[bool, List[int], str]:
    """
    Parse a page range string (1-based), e.g. '1-3, 5, 8-10'.
    Validates:
      - Empty strings
      - Characters (only digits, commas, hyphens, spaces allowed)
      - No page <= 0
      - No reverse ranges (e.g. '5-2')
      - No pages > max_pages
      - No duplicate pages
    Returns: (is_valid, list_of_pages, error_message)
    """
    if not range_str or not range_str.strip():
        return False, [], "Rentang halaman tidak boleh kosong."

    clean_str = range_str.strip()

    # Disallow invalid consecutive symbols or invalid characters
    if not re.match(r"^[\d\s,-]+$", clean_str):
        return False, [], "Input hanya boleh berisi angka, tanda hubung (-), koma, dan spasi."

    # Check for trailing or leading commas or double commas
    parts = clean_str.split(",")
    parsed_pages: List[int] = []
    seen_pages = set()

    for raw_part in parts:
        part = raw_part.strip()
        if not part:
            return False, [], "Format rentang tidak valid (ditemukan koma kosong)."

        if "-" in part:
            subparts = part.split("-")
            if len(subparts) != 2:
                return False, [], f"Format rentang '{part}' tidak valid."

            start_str, end_str = subparts[0].strip(), subparts[1].strip()
            if not start_str.isdigit() or not end_str.isdigit():
                return False, [], f"Format rentang '{part}' harus berupa angka."

            start_page, end_page = int(start_str), int(end_str)

            if start_page < 1:
                return False, [], "Nomor halaman tidak boleh 0 atau negatif."
            if start_page > end_page:
                return False, [], f"Rentang terbalik '{part}' tidak valid (halaman awal harus lebih kecil dari akhir)."
            if end_page > max_pages:
                return False, [], f"Halaman {end_page} melebihi jumlah total halaman ({max_pages})."

            for p in range(start_page, end_page + 1):
                if p in seen_pages:
                    return False, [], f"Halaman duplikat ditemukan: {p}. Setiap nomor halaman hanya boleh dimasukkan satu kali."
                seen_pages.add(p)
                parsed_pages.append(p)
        else:
            if not part.isdigit():
                return False, [], f"Nilai '{part}' bukan angka yang valid."

            p = int(part)
            if p < 1:
                return False, [], "Nomor halaman tidak boleh 0 atau negatif."
            if p > max_pages:
                return False, [], f"Halaman {p} melebihi jumlah total halaman ({max_pages})."
            if p in seen_pages:
                return False, [], f"Halaman duplikat ditemukan: {p}. Setiap nomor halaman hanya boleh dimasukkan satu kali."
            seen_pages.add(p)
            parsed_pages.append(p)

    if not parsed_pages:
        return False, [], "Tidak ada halaman yang dipilih."

    return True, parsed_pages, ""
