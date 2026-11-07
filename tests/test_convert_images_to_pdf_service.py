import os
from PIL import Image
import pymupdf as fitz
import pytest

from app.services.convert_images_to_pdf_service import (
    A4_HEIGHT,
    A4_WIDTH,
    convert_images_to_pdf,
    is_supported_image,
    prepare_image_for_pdf,
    validate_image_file,
)


def create_sample_image(path: str, size: tuple[int, int] = (200, 100), mode: str = "RGB", color: tuple = (255, 0, 0)) -> str:
    img = Image.new(mode, size, color)
    img.save(path)
    return path


def test_is_supported_image():
    assert is_supported_image("test.jpg") is True
    assert is_supported_image("test.JPEG") is True
    assert is_supported_image("path/to/image.png") is True
    assert is_supported_image("image.bmp") is True
    assert is_supported_image("image.TIFF") is True
    assert is_supported_image("image.tif") is True
    assert is_supported_image("image.webp") is True
    assert is_supported_image("document.pdf") is False
    assert is_supported_image("notes.txt") is False
    assert is_supported_image("animation.gif") is False


def test_validate_image_file(tmp_path):
    # Valid PNG image
    img_path = str(tmp_path / "valid.png")
    create_sample_image(img_path, (320, 240), mode="RGB")
    valid, err, info = validate_image_file(img_path)
    assert valid is True
    assert err == ""
    assert info["filename"] == "valid.png"
    assert info["width"] == 320
    assert info["height"] == 240
    assert info["format"] == "PNG"

    # Non-existent file
    valid, err, info = validate_image_file(str(tmp_path / "missing.png"))
    assert valid is False
    assert "tidak ditemukan" in err

    # Corrupt/empty file
    corrupt_path = str(tmp_path / "corrupt.jpg")
    with open(corrupt_path, "wb") as f:
        f.write(b"not an image data")
    valid, err, info = validate_image_file(corrupt_path)
    assert valid is False
    assert "tidak dapat" in err


def test_prepare_image_for_pdf_rgba(tmp_path):
    # Test transparency conversion to RGB with white background
    img_path = str(tmp_path / "transparent.png")
    # Half-transparent blue
    img = Image.new("RGBA", (100, 100), (0, 0, 255, 128))
    img.save(img_path)

    img_bytes, w, h = prepare_image_for_pdf(img_path)
    assert isinstance(img_bytes, bytes)
    assert (w, h) == (100, 100)

    # Verify bytes can be decoded
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    page.insert_image(fitz.Rect(0, 0, 100, 100), stream=img_bytes)
    assert len(doc) == 1
    doc.close()


def test_convert_images_to_pdf_empty_list(tmp_path):
    out_pdf = str(tmp_path / "out.pdf")
    ok, msg, data = convert_images_to_pdf([], out_pdf)
    assert ok is False
    assert "Tidak ada gambar" in msg


def test_convert_images_to_pdf_fit_to_image(tmp_path):
    img1 = create_sample_image(str(tmp_path / "img1.png"), (400, 300), color=(255, 0, 0))
    img2 = create_sample_image(str(tmp_path / "img2.jpg"), (600, 800), color=(0, 255, 0))
    out_pdf = str(tmp_path / "combined_fit.pdf")

    progress_reports = []

    def on_progress(cur, total, msg):
        progress_reports.append((cur, total, msg))

    ok, msg, data = convert_images_to_pdf(
        [img1, img2],
        out_pdf,
        page_format="fit_to_image",
        progress_callback=on_progress,
    )

    assert ok is True
    assert os.path.exists(out_pdf)
    assert data["total_pages"] == 2
    assert len(progress_reports) >= 2

    # Verify PDF content with PyMuPDF
    doc = fitz.open(out_pdf)
    assert len(doc) == 2

    # Page 1 matches img1 dimensions (400 x 300)
    p1 = doc[0]
    assert abs(p1.rect.width - 400) < 1.0
    assert abs(p1.rect.height - 300) < 1.0

    # Page 2 matches img2 dimensions (600 x 800)
    p2 = doc[1]
    assert abs(p2.rect.width - 600) < 1.0
    assert abs(p2.rect.height - 800) < 1.0
    doc.close()


def test_convert_images_to_pdf_a4_portrait(tmp_path):
    img1 = create_sample_image(str(tmp_path / "img1.png"), (1000, 500))
    out_pdf = str(tmp_path / "a4_portrait.pdf")

    ok, msg, data = convert_images_to_pdf(
        [img1],
        out_pdf,
        page_format="a4_portrait",
        margin_mm=5.0,
    )

    assert ok is True
    doc = fitz.open(out_pdf)
    assert len(doc) == 1
    p = doc[0]
    assert abs(p.rect.width - A4_WIDTH) < 0.1
    assert abs(p.rect.height - A4_HEIGHT) < 0.1
    doc.close()


def test_convert_images_to_pdf_a4_landscape(tmp_path):
    img1 = create_sample_image(str(tmp_path / "img1.png"), (500, 1000))
    out_pdf = str(tmp_path / "a4_landscape.pdf")

    ok, msg, data = convert_images_to_pdf(
        [img1],
        out_pdf,
        page_format="a4_landscape",
        margin_mm=12.0,
    )

    assert ok is True
    doc = fitz.open(out_pdf)
    assert len(doc) == 1
    p = doc[0]
    assert abs(p.rect.width - A4_HEIGHT) < 0.1
    assert abs(p.rect.height - A4_WIDTH) < 0.1
    doc.close()


def test_convert_images_to_pdf_cancellation(tmp_path):
    img1 = create_sample_image(str(tmp_path / "img1.png"), (300, 300))
    img2 = create_sample_image(str(tmp_path / "img2.png"), (300, 300))
    out_pdf = str(tmp_path / "cancelled.pdf")

    cancel_flag = False

    def check_cancel():
        return cancel_flag

    def on_progress(cur, total, msg):
        nonlocal cancel_flag
        if cur >= 1:
            cancel_flag = True

    ok, msg, data = convert_images_to_pdf(
        [img1, img2],
        out_pdf,
        progress_callback=on_progress,
        is_cancelled_callback=check_cancel,
    )

    assert ok is False
    assert "dibatalkan" in msg
    assert not os.path.exists(out_pdf)
