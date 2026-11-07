import os
from PIL import Image, ImageDraw
import pytest

from app.services.background_changer_service import (
    BACKGROUND_COLORS,
    PAS_FOTO_SPECS,
    SUPPORTED_IMAGE_EXTENSIONS,
    apply_background_color,
    crop_to_pas_foto,
    is_supported_image,
    load_and_orient_image,
    remove_background,
    save_result_image,
    validate_image_file,
)


def create_sample_image(path: str, size: tuple[int, int] = (200, 200), mode: str = "RGB", color: tuple = (255, 0, 0)) -> str:
    img = Image.new(mode, size, color)
    img.save(path)
    return path


def test_standardized_background_colors():
    """Verify exactly 5 standardized colors with specified HEX codes."""
    assert len(BACKGROUND_COLORS) == 5
    expected_colors = {
        "Merah": "#D9001B",
        "Biru": "#0056A6",
        "Putih": "#FFFFFF",
        "Kuning": "#FFD700",
        "Hijau": "#00843D",
    }
    for name, hex_code in expected_colors.items():
        assert name in BACKGROUND_COLORS
        assert BACKGROUND_COLORS[name]["hex"].upper() == hex_code.upper()
        assert len(BACKGROUND_COLORS[name]["rgb"]) == 3


def test_pas_foto_specs():
    """Verify pas foto specifications."""
    assert "Original" in PAS_FOTO_SPECS
    assert "2 × 3 cm" in PAS_FOTO_SPECS
    assert "3 × 4 cm" in PAS_FOTO_SPECS
    assert "4 × 6 cm" in PAS_FOTO_SPECS


def test_is_supported_image():
    assert is_supported_image("photo.jpg") is True
    assert is_supported_image("photo.JPEG") is True
    assert is_supported_image("photo.png") is True
    assert is_supported_image("photo.webp") is True
    assert is_supported_image("photo.bmp") is True
    assert is_supported_image("doc.pdf") is False
    assert is_supported_image("notes.txt") is False


def test_validate_image_file(tmp_path):
    # 1. Valid image
    img_path = str(tmp_path / "test.jpg")
    create_sample_image(img_path, (300, 400), "RGB", (100, 150, 200))
    ok, err, meta = validate_image_file(img_path)
    assert ok is True
    assert err == ""
    assert meta["width"] == 300
    assert meta["height"] == 400
    assert meta["filename"] == "test.jpg"

    # 2. Non-existent file
    ok, err, meta = validate_image_file(str(tmp_path / "not_found.jpg"))
    assert ok is False
    assert "tidak ditemukan" in err

    # 3. Corrupt file
    corrupt_path = str(tmp_path / "bad.jpg")
    with open(corrupt_path, "wb") as f:
        f.write(b"not image content")
    ok, err, meta = validate_image_file(corrupt_path)
    assert ok is False
    assert "rusak" in err

    # 4. Oversized resolution file (> 8000px)
    huge_path = str(tmp_path / "huge.png")
    # Create small header with huge dimensions in PNG or test logic
    with Image.new("RGB", (8500, 100), (0, 0, 0)) as huge_img:
        huge_img.save(huge_path)
    ok, err, meta = validate_image_file(huge_path)
    assert ok is False
    assert "Resolusi gambar terlalu besar" in err


def test_apply_background_color():
    """Verify compositing foreground over 5 standardized colors."""
    # Create an RGBA image: transparent background with an opaque green square in the center
    fg = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(fg)
    draw.rectangle([25, 25, 75, 75], fill=(0, 255, 0, 255))

    for color_name, spec in BACKGROUND_COLORS.items():
        comp = apply_background_color(fg, color_name)
        assert comp.mode == "RGB"
        assert comp.size == (100, 100)

        # Corner (0,0) was transparent, should now be exact background color
        corner_pixel = comp.getpixel((0, 0))
        assert corner_pixel == spec["rgb"]

        # Center (50,50) was opaque green, should remain green
        center_pixel = comp.getpixel((50, 50))
        assert center_pixel == (0, 255, 0)


def test_crop_to_pas_foto():
    # Source image: 600 x 800 (ratio 0.75)
    src = Image.new("RGB", (600, 800), (200, 200, 200))

    # Original retains dimensions
    orig = crop_to_pas_foto(src, "Original")
    assert orig.size == (600, 800)

    # 2x3 cm at 300 DPI
    p2x3 = crop_to_pas_foto(src, "2 × 3 cm", dpi=300)
    assert p2x3.size[0] == int(round(2.0 / 2.54 * 300))
    assert p2x3.size[1] == int(round(3.0 / 2.54 * 300))

    # 3x4 cm at 300 DPI
    p3x4 = crop_to_pas_foto(src, "3 × 4 cm", dpi=300)
    assert p3x4.size[0] == int(round(2.8 / 2.54 * 300))
    assert p3x4.size[1] == int(round(3.8 / 2.54 * 300))

    # 4x6 cm at 300 DPI
    p4x6 = crop_to_pas_foto(src, "4 × 6 cm", dpi=300)
    assert p4x6.size[0] == int(round(3.8 / 2.54 * 300))
    assert p4x6.size[1] == int(round(5.6 / 2.54 * 300))


def test_save_result_image(tmp_path):
    img = Image.new("RGB", (200, 300), (217, 0, 27))

    # 1. Save as JPG
    jpg_path = str(tmp_path / "result.jpg")
    ok, res_path = save_result_image(img, jpg_path, format_type="JPG")
    assert ok is True
    assert os.path.exists(res_path)
    with Image.open(res_path) as saved:
        assert saved.format == "JPEG"
        assert saved.size == (200, 300)

    # 2. Save as PNG
    png_path = str(tmp_path / "result.png")
    ok, res_path = save_result_image(img, png_path, format_type="PNG")
    assert ok is True
    assert os.path.exists(res_path)
    with Image.open(res_path) as saved:
        assert saved.format == "PNG"
        assert saved.size == (200, 300)


def test_remove_background_execution():
    """Verify rembg AI inference runs and returns RGBA image with correct size."""
    # Create simple image: white circle on black background
    img = Image.new("RGB", (80, 80), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([20, 20, 60, 60], fill=(255, 255, 255))

    result_fg = remove_background(img, model_name="u2netp")
    assert result_fg is not None
    assert result_fg.mode == "RGBA"
    assert result_fg.size == (80, 80)

