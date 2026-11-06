import os
from typing import Any, Callable, Dict, Optional, Tuple
import pymupdf as fitz

from app.utils.file_utils import format_file_size
from app.utils.validators import validate_output_filename, validate_pdf_file

# Centralized preset configuration as specified in Section 3
PRESET_CONFIGS: Dict[str, Dict[str, Any]] = {
    "high": {
        "name": "Kualitas Tinggi",
        "description": "Menjaga kualitas visual. Optimasi struktur dan stream; hindari downsampling agresif.",
        "dpi_threshold": 200,
        "dpi_target": 150,
        "quality": 85,
        "lossless": False,
        "garbage": 4,
        "clean": True,
        "deflate": True,
        "deflate_images": True,
        "deflate_fonts": True,
        "use_objstms": 1,
    },
    "balanced": {
        "name": "Seimbang",
        "description": "Kompromi ukuran dan kualitas. Optimasi struktur dan kompresi gambar moderat.",
        "dpi_threshold": 150,
        "dpi_target": 120,
        "quality": 65,
        "lossless": True,
        "garbage": 4,
        "clean": True,
        "deflate": True,
        "deflate_images": True,
        "deflate_fonts": True,
        "use_objstms": 1,
    },
    "small": {
        "name": "Ukuran Lebih Kecil",
        "description": "Memprioritaskan ukuran file. Downsampling gambar lebih agresif; kualitas visual dapat menurun.",
        "dpi_threshold": 100,
        "dpi_target": 72,
        "quality": 45,
        "lossless": True,
        "garbage": 4,
        "clean": True,
        "deflate": True,
        "deflate_images": True,
        "deflate_fonts": True,
        "use_objstms": 1,
    },
}


def calculate_compression_metrics(original_size: int, compressed_size: int) -> Dict[str, Any]:
    """
    Calculate size reduction and percentage according to Section 7 guidelines.
    Positive saved_bytes: size reduced.
    Zero: size unchanged.
    Negative: size increased.
    """
    saved_bytes = original_size - compressed_size
    if original_size > 0:
        change_percent = (saved_bytes / original_size) * 100.0
    else:
        change_percent = 0.0

    is_larger = compressed_size > original_size
    is_same = compressed_size == original_size

    if is_larger:
        diff_bytes = compressed_size - original_size
        pct = abs(change_percent)
        summary_text = f"Ukuran bertambah {format_file_size(diff_bytes)} (+{pct:.1f}%)"
    elif is_same:
        summary_text = "Ukuran tidak berubah (0%)"
    else:
        summary_text = f"Hemat {format_file_size(saved_bytes)} ({change_percent:.1f}%)"

    return {
        "original_size": original_size,
        "compressed_size": compressed_size,
        "saved_bytes": saved_bytes,
        "change_percent": change_percent,
        "is_larger": is_larger,
        "is_same": is_same,
        "summary_text": summary_text,
    }


def compress_pdf(
    input_path: str,
    output_path: str,
    preset: str = "balanced",
    password: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Compress a single PDF file using structural optimization and image recompression.

    Parameters:
        input_path: Path to the input PDF file.
        output_path: Path to the target compressed PDF file.
        preset: 'high', 'balanced', or 'small' (default: 'balanced').
        password: Password if PDF is encrypted.
        progress_callback: Optional callback(current, total, status_message).

    Returns:
        (success: bool, message: str, result_data: Optional[dict])
    """
    if not input_path or not os.path.exists(input_path):
        return False, "Silakan pilih file PDF terlebih dahulu.", None

    if not output_path or not output_path.strip():
        return False, "Lokasi file output belum ditentukan.", None

    norm_input = os.path.normcase(os.path.abspath(input_path))
    norm_output = os.path.normcase(os.path.abspath(output_path))
    if norm_input == norm_output:
        return False, "File output tidak boleh sama dengan file sumber.", None

    out_filename = os.path.basename(output_path)
    ok, err_name = validate_output_filename(out_filename)
    if not ok:
        return False, err_name, None

    # Validate destination directory
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return False, f"Folder tujuan tidak dapat diakses: {str(e)}", None

    # Validate input PDF
    is_valid, err_msg, page_count = validate_pdf_file(input_path, password=password)
    if not is_valid:
        return False, err_msg, None

    cfg = PRESET_CONFIGS.get(preset, PRESET_CONFIGS["balanced"])
    original_size = os.path.getsize(input_path)

    doc = None
    try:
        if progress_callback:
            progress_callback(10, 100, "Membuka dokumen...")

        doc = fitz.open(input_path)
        if doc.is_encrypted:
            auth_rc = doc.authenticate(password or "")
            if auth_rc == 0:
                doc.close()
                return False, "PDF ini dilindungi password. Masukkan password atau pilih file lain.", None

        if progress_callback:
            progress_callback(35, 100, "Mengoptimalkan gambar dan struktur stream...")

        # Recompress images according to selected preset
        try:
            doc.rewrite_images(
                dpi_threshold=cfg.get("dpi_threshold", 150),
                dpi_target=cfg.get("dpi_target", 120),
                quality=cfg.get("quality", 65),
                lossy=True,
                lossless=cfg.get("lossless", True),
            )
        except Exception:
            # Fall back to stream optimization if image rewriting encounters unsupported image formats
            pass

        if progress_callback:
            progress_callback(75, 100, "Menyimpan dokumen terkompresi...")

        # Save with garbage collection, deflate streams, object streams, and metadata preservation
        try:
            doc.save(
                output_path,
                garbage=cfg.get("garbage", 4),
                clean=cfg.get("clean", True),
                deflate=cfg.get("deflate", True),
                deflate_images=cfg.get("deflate_images", True),
                deflate_fonts=cfg.get("deflate_fonts", True),
                use_objstms=cfg.get("use_objstms", 1),
                preserve_metadata=1,
            )
        except Exception:
            # If clean=True fails on rare malformed stream syntax, retry with clean=False
            doc.save(
                output_path,
                garbage=cfg.get("garbage", 4),
                clean=False,
                deflate=cfg.get("deflate", True),
                deflate_images=cfg.get("deflate_images", True),
                deflate_fonts=cfg.get("deflate_fonts", True),
                use_objstms=cfg.get("use_objstms", 1),
                preserve_metadata=1,
            )

        doc.close()
        doc = None

        if not os.path.exists(output_path):
            return False, "Proses kompresi gagal: File hasil tidak terbentuk. File asli tetap aman.", None

        compressed_size = os.path.getsize(output_path)
        metrics = calculate_compression_metrics(original_size, compressed_size)
        metrics["output_path"] = output_path
        metrics["page_count"] = page_count
        metrics["preset"] = preset

        if progress_callback:
            progress_callback(100, 100, "Kompresi berhasil diselesaikan.")

        return True, "Dokumen PDF berhasil dikompresi.", metrics

    except Exception as e:
        if doc:
            try:
                doc.close()
            except Exception:
                pass

        # Ensure no partial or corrupted file remains
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

        return False, f"Proses kompresi gagal: {str(e)}. File asli tetap aman.", None

