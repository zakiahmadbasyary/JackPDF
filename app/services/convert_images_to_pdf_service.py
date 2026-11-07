"""
convert_images_to_pdf_service.py - Core image-to-PDF conversion logic for JackPDF.

Supports JPG, JPEG, PNG, BMP, TIFF, TIF, and WEBP formats with EXIF orientation,
transparency handling, and multiple page layout options (Fit to Image, A4 Portrait, A4 Landscape).
"""

import io
import os
from typing import Any, Callable, Dict, List, Optional, Tuple
from PIL import Image, ImageOps
import pymupdf as fitz

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
}

# A4 Dimensions in points (72 points per inch)
A4_WIDTH = 595.3
A4_HEIGHT = 841.9


def is_supported_image(file_path: str) -> bool:
    """Check if the given file has a supported image extension."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SUPPORTED_IMAGE_EXTENSIONS


def validate_image_file(file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate an image file for conversion.
    Returns:
        (is_valid, error_message, metadata_dict)
    Metadata contains:
        path, filename, width, height, format, mode, size_bytes
    """
    if not os.path.exists(file_path):
        return False, "File tidak ditemukan.", {}

    if not is_supported_image(file_path):
        ext = os.path.splitext(file_path)[1]
        return False, f"Format file '{ext}' tidak didukung. Gunakan JPG, PNG, BMP, TIFF, atau WEBP.", {}

    try:
        with Image.open(file_path) as img:
            # Handle EXIF orientation so reported dimensions match orientation
            transposed = ImageOps.exif_transpose(img)
            width, height = transposed.size
            format_name = img.format or os.path.splitext(file_path)[1].lstrip(".").upper()
            mode = img.mode
            file_size = os.path.getsize(file_path)

            return True, "", {
                "path": os.path.abspath(file_path),
                "filename": os.path.basename(file_path),
                "width": width,
                "height": height,
                "format": format_name,
                "mode": mode,
                "size_bytes": file_size,
            }
    except Exception as e:
        return False, f"File rusak atau tidak dapat didekode: {str(e)}", {}


def prepare_image_for_pdf(file_path: str) -> Tuple[bytes, int, int]:
    """
    Open, transpose via EXIF, flatten transparency on white background,
    and encode into JPEG bytes ready for PDF insertion.
    Returns:
        (image_bytes, width, height)
    """
    with Image.open(file_path) as raw_img:
        # Correct orientation based on EXIF tags
        img = ImageOps.exif_transpose(raw_img)

        # Handle alpha channel / transparency with clean white background
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img_rgba = img.convert("RGBA")
            bg = Image.new("RGB", img_rgba.size, (255, 255, 255))
            bg.paste(img_rgba, mask=img_rgba.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        bio = io.BytesIO()
        # High quality JPEG for clean PDF rendering without excessive bloat
        img.save(bio, format="JPEG", quality=95)
        return bio.getvalue(), w, h


def convert_images_to_pdf(
    image_paths: List[str],
    output_path: str,
    page_format: str = "fit_to_image",
    margin_mm: float = 0.0,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    is_cancelled_callback: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Convert a list of image files to a single multi-page PDF document.

    Args:
        image_paths: List of absolute file paths to images in display order.
        output_path: Absolute destination path for the PDF.
        page_format: 'fit_to_image', 'a4_portrait', or 'a4_landscape'.
        margin_mm: Margin size in millimeters (default 0.0).
        progress_callback: Function called as callback(current, total, message).
        is_cancelled_callback: Function checking if process was cancelled.

    Returns:
        (success, message, result_data)
    """
    if not image_paths:
        return False, "Tidak ada gambar yang dipilih untuk dikonversi.", None

    if not output_path or not output_path.strip():
        return False, "Lokasi file output belum ditentukan.", None

    norm_output = os.path.abspath(output_path.strip())
    if not norm_output.lower().endswith(".pdf"):
        norm_output += ".pdf"

    # Validate output folder is writable
    out_dir = os.path.dirname(norm_output)
    if not os.path.exists(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            return False, f"Folder output tidak dapat dibuat: {str(e)}", None

    total_images = len(image_paths)
    doc = fitz.open()

    margin_pt = margin_mm * 72.0 / 25.4

    try:
        for idx, img_path in enumerate(image_paths, start=1):
            if is_cancelled_callback and is_cancelled_callback():
                doc.close()
                return False, "Proses konversi dibatalkan oleh pengguna.", {"is_cancelled": True}

            fname = os.path.basename(img_path)
            if progress_callback:
                progress_callback(idx, total_images, f"Memproses gambar {idx}/{total_images}: {fname}")

            # Read and prepare image
            try:
                img_bytes, img_w, img_h = prepare_image_for_pdf(img_path)
            except Exception as e:
                doc.close()
                return False, f"Gagal memproses gambar '{fname}': {str(e)}", None

            # Determine page size and target insertion rect
            if page_format == "a4_portrait":
                page_w, page_h = A4_WIDTH, A4_HEIGHT
                avail_w = max(10.0, page_w - 2 * margin_pt)
                avail_h = max(10.0, page_h - 2 * margin_pt)
                scale = min(avail_w / img_w, avail_h / img_h)
                fw = img_w * scale
                fh = img_h * scale
                x0 = margin_pt + (avail_w - fw) / 2.0
                y0 = margin_pt + (avail_h - fh) / 2.0
                rect = fitz.Rect(x0, y0, x0 + fw, y0 + fh)

            elif page_format == "a4_landscape":
                page_w, page_h = A4_HEIGHT, A4_WIDTH
                avail_w = max(10.0, page_w - 2 * margin_pt)
                avail_h = max(10.0, page_h - 2 * margin_pt)
                scale = min(avail_w / img_w, avail_h / img_h)
                fw = img_w * scale
                fh = img_h * scale
                x0 = margin_pt + (avail_w - fw) / 2.0
                y0 = margin_pt + (avail_h - fh) / 2.0
                rect = fitz.Rect(x0, y0, x0 + fw, y0 + fh)

            else:  # "fit_to_image" (default)
                page_w = img_w + 2 * margin_pt
                page_h = img_h + 2 * margin_pt
                rect = fitz.Rect(margin_pt, margin_pt, margin_pt + img_w, margin_pt + img_h)

            page = doc.new_page(width=page_w, height=page_h)
            page.insert_image(rect, stream=img_bytes)

        if is_cancelled_callback and is_cancelled_callback():
            doc.close()
            return False, "Proses konversi dibatalkan oleh pengguna.", {"is_cancelled": True}

        if progress_callback:
            progress_callback(total_images, total_images, "Menyimpan dokumen PDF...")

        doc.save(norm_output, garbage=4, deflate=True)
        doc.close()

        file_size = os.path.getsize(norm_output)

        return True, "Gambar berhasil dikonversi ke PDF.", {
            "output_path": norm_output,
            "total_pages": total_images,
            "file_size": file_size,
        }

    except Exception as e:
        try:
            doc.close()
        except Exception:
            pass
        # Clean up partial output if created during failed run
        if os.path.exists(norm_output):
            try:
                os.remove(norm_output)
            except Exception:
                pass
        return False, f"Terjadi kesalahan saat membuat PDF: {str(e)}", None

