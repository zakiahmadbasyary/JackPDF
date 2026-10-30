import os
from typing import Callable, List, Optional, Tuple
import pymupdf as fitz

from app.utils.file_utils import get_safe_destination_path
from app.utils.validators import parse_page_range, validate_pdf_file


def split_pdf_by_range(
    input_path: str,
    range_str: str,
    output_path: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[bool, str, List[str]]:
    """
    Export specific page range (e.g. '1-3, 5, 8-10') into a single output PDF.
    """
    is_valid, err_msg, total_pages = validate_pdf_file(input_path)
    if not is_valid:
        return False, err_msg, []

    range_valid, pages, range_err = parse_page_range(range_str, total_pages)
    if not range_valid:
        return False, range_err, []

    norm_in = os.path.normcase(os.path.abspath(input_path))
    norm_out = os.path.normcase(os.path.abspath(output_path))
    if norm_in == norm_out:
        return (
            False,
            "File output tidak boleh sama dengan file input.",
            [],
        )

    output_dir = os.path.dirname(os.path.abspath(output_path))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    src_doc = None
    out_doc = None
    try:
        src_doc = fitz.open(input_path)
        out_doc = fitz.open()

        total_to_extract = len(pages)
        for idx, page_num in enumerate(pages):
            if progress_callback:
                progress_callback(
                    idx,
                    total_to_extract,
                    f"Mengekstrak halaman {page_num} ({idx + 1}/{total_to_extract})...",
                )
            # fitz is 0-based
            page_idx = page_num - 1
            out_doc.insert_pdf(src_doc, from_page=page_idx, to_page=page_idx)

        if progress_callback:
            progress_callback(total_to_extract, total_to_extract, "Menyimpan file hasil...")

        out_doc.save(output_path, garbage=3, deflate=True)
        out_doc.close()
        out_doc = None
        src_doc.close()
        src_doc = None

        return (
            True,
            f"Berhasil mengekstrak {total_to_extract} halaman ke '{os.path.basename(output_path)}'.",
            [output_path],
        )
    except Exception as e:
        if out_doc:
            try:
                out_doc.close()
            except Exception:
                pass
        if src_doc:
            try:
                src_doc.close()
            except Exception:
                pass
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        return False, f"Pemisahan halaman gagal: {str(e)}", []


def split_pdf_each_page(
    input_path: str,
    output_dir: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[bool, str, List[str]]:
    """
    Split PDF into one file per page (e.g. 'doc_page_001.pdf').
    """
    is_valid, err_msg, total_pages = validate_pdf_file(input_path)
    if not is_valid:
        return False, err_msg, []

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    generated_files: List[str] = []
    src_doc = None

    try:
        src_doc = fitz.open(input_path)
        for page_idx in range(total_pages):
            page_num = page_idx + 1
            if progress_callback:
                progress_callback(
                    page_idx,
                    total_pages,
                    f"Membuat file halaman {page_num} dari {total_pages}...",
                )

            filename = f"{base_name}_page_{page_num:03d}.pdf"
            dest_path = get_safe_destination_path(output_dir, filename)

            single_doc = fitz.open()
            single_doc.insert_pdf(src_doc, from_page=page_idx, to_page=page_idx)
            single_doc.save(dest_path, garbage=3, deflate=True)
            single_doc.close()
            generated_files.append(dest_path)

        src_doc.close()
        src_doc = None

        return (
            True,
            f"Berhasil memisahkan {total_pages} halaman menjadi {len(generated_files)} file PDF.",
            generated_files,
        )
    except Exception as e:
        if src_doc:
            try:
                src_doc.close()
            except Exception:
                pass
        # Clean up partial generated files on error
        for f in generated_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        return False, f"Pemisahan per halaman gagal: {str(e)}", []


def split_pdf_fixed_size(
    input_path: str,
    output_dir: str,
    pages_per_file: int,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[bool, str, List[str]]:
    """
    Split PDF into chunks of fixed size (e.g. 'doc_part_001.pdf').
    """
    if pages_per_file < 1:
        return False, "Jumlah halaman per file minimal 1.", []

    is_valid, err_msg, total_pages = validate_pdf_file(input_path)
    if not is_valid:
        return False, err_msg, []

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    generated_files: List[str] = []
    src_doc = None

    try:
        src_doc = fitz.open(input_path)
        chunks = []
        for start in range(0, total_pages, pages_per_file):
            end = min(start + pages_per_file - 1, total_pages - 1)
            chunks.append((start, end))

        total_chunks = len(chunks)
        for idx, (start_idx, end_idx) in enumerate(chunks):
            part_num = idx + 1
            if progress_callback:
                progress_callback(
                    idx,
                    total_chunks,
                    f"Membuat bagian {part_num} dari {total_chunks} (hal {start_idx + 1}-{end_idx + 1})...",
                )

            filename = f"{base_name}_part_{part_num:03d}.pdf"
            dest_path = get_safe_destination_path(output_dir, filename)

            part_doc = fitz.open()
            part_doc.insert_pdf(src_doc, from_page=start_idx, to_page=end_idx)
            part_doc.save(dest_path, garbage=3, deflate=True)
            part_doc.close()
            generated_files.append(dest_path)

        src_doc.close()
        src_doc = None

        return (
            True,
            f"Berhasil membagi dokumen menjadi {total_chunks} file PDF.",
            generated_files,
        )
    except Exception as e:
        if src_doc:
            try:
                src_doc.close()
            except Exception:
                pass
        for f in generated_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        return False, f"Pemisahan rentang tetap gagal: {str(e)}", []


def split_pdf_multi_ranges(
    input_path: str,
    ranges: List[Tuple[int, int]],
    destination: str,
    merge_ranges: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[bool, str, List[str]]:
    """
    Split a PDF based on multiple page ranges.

    If merge_ranges is True:
        All specified ranges are merged into a single output PDF at `destination` (file path).
    If merge_ranges is False:
        Each range is exported to its own PDF file inside `destination` (directory path).
    """
    is_valid, err_msg, total_pages = validate_pdf_file(input_path)
    if not is_valid:
        return False, err_msg, []

    if not ranges:
        return False, "Tidak ada rentang halaman yang ditentukan.", []

    # Validate each range
    for idx, (start, end) in enumerate(ranges):
        if start < 1 or end > total_pages:
            return (
                False,
                f"Rentang {idx + 1} (hal {start}-{end}) berada di luar batas halaman (1-{total_pages}).",
                [],
            )
        if start > end:
            return (
                False,
                f"Rentang {idx + 1} tidak valid: halaman awal ({start}) lebih besar dari halaman akhir ({end}).",
                [],
            )

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    generated_files: List[str] = []
    src_doc = None

    if merge_ranges:
        norm_in = os.path.normcase(os.path.abspath(input_path))
        norm_out = os.path.normcase(os.path.abspath(destination))
        if norm_in == norm_out:
            return False, "File output tidak boleh sama dengan file input.", []

        output_dir = os.path.dirname(os.path.abspath(destination))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        out_doc = None
        try:
            src_doc = fitz.open(input_path)
            out_doc = fitz.open()

            total_pages_to_extract = sum(end - start + 1 for start, end in ranges)
            extracted_so_far = 0

            for idx, (start, end) in enumerate(ranges):
                if progress_callback:
                    progress_callback(
                        extracted_so_far,
                        total_pages_to_extract,
                        f"Mengekstrak rentang {idx + 1} (hal {start}-{end})...",
                    )
                # insert_pdf from_page and to_page are 0-indexed inclusive
                out_doc.insert_pdf(src_doc, from_page=start - 1, to_page=end - 1)
                extracted_so_far += (end - start + 1)

            if progress_callback:
                progress_callback(total_pages_to_extract, total_pages_to_extract, "Menyimpan file hasil...")

            out_doc.save(destination, garbage=3, deflate=True)
            out_doc.close()
            out_doc = None
            src_doc.close()
            src_doc = None

            return (
                True,
                f"Berhasil menggabungkan {len(ranges)} rentang ({total_pages_to_extract} halaman) ke '{os.path.basename(destination)}'.",
                [destination],
            )
        except Exception as e:
            if out_doc:
                try:
                    out_doc.close()
                except Exception:
                    pass
            if src_doc:
                try:
                    src_doc.close()
                except Exception:
                    pass
            if os.path.exists(destination):
                try:
                    os.remove(destination)
                except Exception:
                    pass
            return False, f"Gagal mengekstrak rentang halaman: {str(e)}", []

    else:
        # Separate files per range
        output_dir = destination
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        try:
            src_doc = fitz.open(input_path)
            total_ranges = len(ranges)

            for idx, (start, end) in enumerate(ranges):
                part_num = idx + 1
                if progress_callback:
                    progress_callback(
                        idx,
                        total_ranges,
                        f"Membuat file rentang {part_num} dari {total_ranges} (hal {start}-{end})...",
                    )

                filename = f"{base_name}_rentang_{part_num}_hal_{start}-{end}.pdf"
                dest_path = get_safe_destination_path(output_dir, filename)

                single_doc = fitz.open()
                single_doc.insert_pdf(src_doc, from_page=start - 1, to_page=end - 1)
                single_doc.save(dest_path, garbage=3, deflate=True)
                single_doc.close()
                generated_files.append(dest_path)

            src_doc.close()
            src_doc = None

            return (
                True,
                f"Berhasil memisahkan {total_ranges} rentang menjadi {len(generated_files)} file PDF.",
                generated_files,
            )
        except Exception as e:
            if src_doc:
                try:
                    src_doc.close()
                except Exception:
                    pass
            for f in generated_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
            return False, f"Gagal memisahkan rentang halaman: {str(e)}", []
