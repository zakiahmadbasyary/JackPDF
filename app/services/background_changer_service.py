"""
background_changer_service.py - AI background removal and replacement service for JackPDF.

Provides:
1. 5 standardized background colors (Merah, Biru, Putih, Kuning, Hijau).
2. Local AI background removal using rembg (u2net / u2net_human_seg / u2netp).
3. EXIF orientation correction and alpha compositing.
4. Formal Pas Foto dimension cropping (2x3, 3x4, 4x6 cm at 300 DPI).
5. High quality JPG and PNG export.
"""

import os
from typing import Any, Callable, Dict, List, Optional, Tuple
from PIL import Image, ImageOps
import rembg

# ---------------------------------------------------------------------------
# 5 Standardized Background Colors (as required by specification)
# ---------------------------------------------------------------------------
BACKGROUND_COLORS: Dict[str, Dict[str, Any]] = {
    "Merah": {
        "name": "Merah",
        "hex": "#D9001B",
        "rgb": (217, 0, 27),
        "desc": "Background pas foto formal merah (Tahun kelahiran ganjil)",
    },
    "Biru": {
        "name": "Biru",
        "hex": "#0056A6",
        "rgb": (0, 86, 166),
        "desc": "Background pas foto formal biru (Tahun kelahiran genap)",
    },
    "Putih": {
        "name": "Putih",
        "hex": "#FFFFFF",
        "rgb": (255, 255, 255),
        "desc": "Background putih (Dokumen visa, paspor, kedutaan)",
    },
    "Kuning": {
        "name": "Kuning",
        "hex": "#FFD700",
        "rgb": (255, 215, 0),
        "desc": "Background kuning (Kebutuhan dokumen instansi tertentu)",
    },
    "Hijau": {
        "name": "Hijau",
        "hex": "#00843D",
        "rgb": (0, 132, 61),
        "desc": "Background hijau (Kebutuhan administrasi khusus)",
    },
}

# ---------------------------------------------------------------------------
# Pas Foto Standard Sizes (Dimensions in cm and standard pixels at 300 DPI)
# ---------------------------------------------------------------------------
PAS_FOTO_SPECS: Dict[str, Dict[str, Any]] = {
    "Original": {
        "label": "Ukuran Asli",
        "width_cm": None,
        "height_cm": None,
        "desc": "Mempertahankan dimensi dan rasio asli gambar",
    },
    "2 × 3 cm": {
        "label": "2 × 3 cm",
        "width_cm": 2.0,
        "height_cm": 3.0,
        "desc": "Ukuran pas foto 2 × 3 cm (236 × 354 px @ 300 DPI)",
    },
    "3 × 4 cm": {
        "label": "3 × 4 cm",
        "width_cm": 2.8,
        "height_cm": 3.8,
        "desc": "Ukuran pas foto 3 × 4 cm (330 × 450 px @ 300 DPI)",
    },
    "4 × 6 cm": {
        "label": "4 × 6 cm",
        "width_cm": 3.8,
        "height_cm": 5.6,
        "desc": "Ukuran pas foto 4 × 6 cm (450 × 660 px @ 300 DPI)",
    },
}

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".tiff",
    ".tif",
}

# Session cache to avoid re-initializing ONNX Runtime session on every run
_CACHED_SESSIONS: Dict[str, Any] = {}


def is_supported_image(file_path: str) -> bool:
    """Check if the given file has a supported image extension."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SUPPORTED_IMAGE_EXTENSIONS


def validate_image_file(file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate that the image file exists and can be decoded by Pillow.
    Returns:
        (is_valid, error_message, metadata_dict)
    """
    if not os.path.exists(file_path):
        return False, "File tidak ditemukan.", {}

    if not is_supported_image(file_path):
        ext = os.path.splitext(file_path)[1]
        return False, f"Format '{ext}' tidak didukung. Gunakan JPG, PNG, WEBP, atau BMP.", {}

    try:
        with Image.open(file_path) as img:
            transposed = ImageOps.exif_transpose(img)
            w, h = transposed.size
            fmt = img.format or os.path.splitext(file_path)[1].lstrip(".").upper()
            file_size = os.path.getsize(file_path)

            # Limit extremely huge dimensions to avoid memory exhaustion (> 8000px)
            if w > 8000 or h > 8000:
                return False, f"Resolusi gambar terlalu besar ({w} × {h} px). Maksimum 8000 × 8000 px.", {}

            return True, "", {
                "path": os.path.abspath(file_path),
                "filename": os.path.basename(file_path),
                "width": w,
                "height": h,
                "format": fmt,
                "size_bytes": file_size,
            }
    except Exception as e:
        return False, f"Gambar rusak atau tidak dapat dibaca: {str(e)}", {}


def load_and_orient_image(file_path: str) -> Image.Image:
    """
    Open an image file, apply EXIF orientation transpose, and return RGB or RGBA Image.
    """
    with Image.open(file_path) as raw:
        img = ImageOps.exif_transpose(raw)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        return img.copy()


def get_model_session(model_name: str = "u2netp"):
    """
    Get or create a cached rembg BaseSession for the specified model name.
    """
    global _CACHED_SESSIONS
    if model_name not in _CACHED_SESSIONS:
        _CACHED_SESSIONS[model_name] = rembg.new_session(model_name)
    return _CACHED_SESSIONS[model_name]


def remove_background(
    image: Image.Image,
    model_name: str = "u2netp",
    post_process: bool = True,
) -> Image.Image:
    """
    Execute AI background removal on the given Pillow image.
    Returns:
        An RGBA Image where the background has alpha = 0.
    """
    session = get_model_session(model_name)
    result = rembg.remove(image, session=session, post_process_mask=post_process)
    if result.mode != "RGBA":
        result = result.convert("RGBA")
    return result


def apply_background_color(
    fg_image: Image.Image,
    color_key_or_hex: str,
) -> Image.Image:
    """
    Composite the foreground RGBA image over a solid background color.

    Args:
        fg_image: Foreground Image in RGBA mode.
        color_key_or_hex: Color name from BACKGROUND_COLORS (e.g. 'Merah') or HEX '#D9001B'.

    Returns:
        Pillow Image in RGB mode with solid background color.
    """
    if fg_image.mode != "RGBA":
        fg_image = fg_image.convert("RGBA")

    if color_key_or_hex in BACKGROUND_COLORS:
        hex_color = BACKGROUND_COLORS[color_key_or_hex]["hex"]
    else:
        hex_color = color_key_or_hex

    # Create solid background canvas
    bg = Image.new("RGBA", fg_image.size, hex_color)
    # Composite foreground with alpha mask
    combined = Image.alpha_composite(bg, fg_image)
    return combined.convert("RGB")


def crop_to_pas_foto(
    image: Image.Image,
    size_key: str,
    dpi: int = 300,
) -> Image.Image:
    """
    Crop and scale image to standard formal Pas Foto aspect ratio and dimensions.

    Args:
        image: Source Pillow Image.
        size_key: 'Original', '2 × 3 cm', '3 × 4 cm', or '4 × 6 cm'.
        dpi: Target DPI for printing (default 300).

    Returns:
        Cropped and resized Image.
    """
    if size_key not in PAS_FOTO_SPECS or size_key == "Original":
        return image.copy()

    spec = PAS_FOTO_SPECS[size_key]
    w_cm = spec["width_cm"]
    h_cm = spec["height_cm"]
    if w_cm is None or h_cm is None:
        return image.copy()

    target_w = int(round(w_cm / 2.54 * dpi))
    target_h = int(round(h_cm / 2.54 * dpi))
    target_ratio = target_w / target_h

    cur_w, cur_h = image.size
    cur_ratio = cur_w / cur_h

    if cur_ratio > target_ratio:
        # Current image is wider than target: crop left and right
        crop_w = int(round(cur_h * target_ratio))
        crop_h = cur_h
        left = (cur_w - crop_w) // 2
        top = 0
    else:
        # Current image is taller than target: crop top and bottom
        # Face bias: in pas foto portraits, bias towards upper portion (15% from top)
        crop_w = cur_w
        crop_h = int(round(cur_w / target_ratio))
        left = 0
        extra_h = cur_h - crop_h
        top = int(round(extra_h * 0.15))

    right = left + crop_w
    bottom = top + crop_h

    # Ensure bounds
    left = max(0, left)
    top = max(0, top)
    right = min(cur_w, right)
    bottom = min(cur_h, bottom)

    cropped = image.crop((left, top, right, bottom))
    resized = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return resized


def save_result_image(
    image: Image.Image,
    output_path: str,
    format_type: str = "JPG",
    dpi: int = 300,
) -> Tuple[bool, str]:
    """
    Save the result image to disk in JPG or PNG format.
    """
    try:
        norm_path = os.path.abspath(output_path.strip())
        out_dir = os.path.dirname(norm_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        fmt_upper = format_type.upper()
        if fmt_upper in ("JPG", "JPEG"):
            if not norm_path.lower().endswith((".jpg", ".jpeg")):
                norm_path += ".jpg"
            # JPG requires RGB mode (no alpha)
            rgb_img = image.convert("RGB") if image.mode != "RGB" else image
            rgb_img.save(norm_path, format="JPEG", quality=95, dpi=(dpi, dpi))
        else:
            if not norm_path.lower().endswith(".png"):
                norm_path += ".png"
            image.save(norm_path, format="PNG", dpi=(dpi, dpi))

        return True, norm_path
    except Exception as e:
        return False, f"Gagal menyimpan file: {str(e)}"

