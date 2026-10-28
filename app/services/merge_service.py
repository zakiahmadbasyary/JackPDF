import os
from typing import Callable, List, Optional, Tuple
import pymupdf as fitz


from app.utils.validators import validate_pdf_file


def merge_pdfs(
    input_paths: List[str],
    output_path: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[bool, str, int]:
    """
    Merge multiple PDF files into one output file.

    Parameters:
        input_paths: List of file paths in the exact desired merge order.
        output_path: Target path for the merged PDF.
        progress_callback: Optional callback(current_idx, total_count, status_text).

    Returns:
        (success: bool, message: str, total_pages: int)
    """
    if not input_paths or len(input_paths) < 2:
        return False, "Minimal harus ada dua file PDF untuk digabungkan.", 0

    if not output_path or not output_path.strip():
        return False, "Lokasi output belum ditentukan.", 0

    # Ensure normalized paths for collision comparison
    norm_output = os.path.normcase(os.path.abspath(output_path))
    for p in input_paths:
        if os.path.normcase(os.path.abspath(p)) == norm_output:
            return (
                False,
                "File output tidak boleh sama dengan salah satu file input yang digabungkan.",
                0,
            )

    # Validate each input file prior to processing
    for idx, path in enumerate(input_paths):
        is_valid, err_msg, _ = validate_pdf_file(path)
        if not is_valid:
            fname = os.path.basename(path)
            return False, f"File '{fname}' tidak valid: {err_msg}", 0

    # Ensure destination directory exists
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return False, f"Tidak dapat membuat direktori output: {output_dir}", 0

    merged_doc = None
    total_files = len(input_paths)
    merged_pages = 0

    try:
        merged_doc = fitz.open()

        for idx, file_path in enumerate(input_paths):
            if progress_callback:
                fname = os.path.basename(file_path)
                progress_callback(
                    idx, total_files, f"Menggabungkan ({idx + 1}/{total_files}): {fname}"
                )

            src_doc = None
            try:
                src_doc = fitz.open(file_path)
                merged_doc.insert_pdf(src_doc)
                src_doc.close()
            except Exception as e:
                if src_doc:
                    try:
                        src_doc.close()
                    except Exception:
                        pass
                raise RuntimeError(
                    f"Gagal membaca halaman dari '{os.path.basename(file_path)}'."
                )

        merged_pages = merged_doc.page_count
        if merged_pages < 1:
            raise RuntimeError("Hasil penggabungan tidak memiliki halaman.")

        if progress_callback:
            progress_callback(total_files, total_files, "Menyimpan file output...")

        # Save to output path
        merged_doc.save(
            output_path,
            garbage=3,
            deflate=True,
        )
        merged_doc.close()
        merged_doc = None

        return (
            True,
            f"Berhasil menggabungkan {total_files} file PDF ({merged_pages} halaman).",
            merged_pages,
        )

    except Exception as e:
        if merged_doc:
            try:
                merged_doc.close()
            except Exception:
                pass

        # Cleanup partial output if created
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

        return False, f"Proses penggabungan gagal: {str(e)}", 0
