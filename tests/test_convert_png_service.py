import os
from PIL import Image
import pymupdf as fitz
import pytest

from app.services.convert_png_service import (
    convert_pdf_to_png,
    get_default_output_dir,
    get_output_filename,
)


def create_test_pdf(path: str, pages: int = 1) -> None:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)  # A4 standard portrait
        page.insert_text((50, 100), f"Halaman {i + 1}")
    doc.save(path)
    doc.close()


def create_encrypted_pdf(path: str, password: str = "pass123") -> None:
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 50), "Dokumen Terenkripsi")
    doc.save(
        path,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=password,
        owner_pw=password,
    )
    doc.close()


# Scenario 1: PDF satu halaman berhasil dikonversi
def test_convert_single_page_pdf(tmp_path):
    pdf = str(tmp_path / "single.pdf")
    out_dir = str(tmp_path / "single_png")
    create_test_pdf(pdf, pages=1)

    ok, msg, data = convert_pdf_to_png(pdf, out_dir, pages=[1], dpi=150)
    assert ok is True
    assert data["total_success"] == 1
    assert len(data["generated_files"]) == 1

    first_file = data["generated_files"][0]
    assert os.path.exists(first_file)
    assert first_file.endswith("single_page-001.png")

    # Verify readable with Pillow
    with Image.open(first_file) as img:
        assert img.format == "PNG"


# Scenario 2 & 3: Semua halaman menghasilkan jumlah PNG sesuai total halaman
def test_convert_all_pages(tmp_path):
    pdf = str(tmp_path / "three_pages.pdf")
    out_dir = str(tmp_path / "three_png")
    create_test_pdf(pdf, pages=3)

    ok, msg, data = convert_pdf_to_png(pdf, out_dir, pages=None, dpi=150)
    assert ok is True
    assert data["total_success"] == 3
    assert len(data["generated_files"]) == 3
    for i in range(1, 4):
        expected_name = f"three_pages_page-00{i}.png"
        assert any(f.endswith(expected_name) for f in data["generated_files"])


# Scenario 4 & 5: Pilihan manual 2, 5, 9 hanya menghasilkan tiga PNG dengan nomor asli
def test_convert_manual_subset_pages(tmp_path):
    pdf = str(tmp_path / "ten_pages.pdf")
    out_dir = str(tmp_path / "subset_png")
    create_test_pdf(pdf, pages=10)

    selected = [2, 5, 9]
    ok, msg, data = convert_pdf_to_png(pdf, out_dir, pages=selected, dpi=200)
    assert ok is True
    assert data["total_success"] == 3
    assert len(data["generated_files"]) == 3

    basenames = [os.path.basename(f) for f in data["generated_files"]]
    assert basenames == [
        "ten_pages_page-002.png",
        "ten_pages_page-005.png",
        "ten_pages_page-009.png",
    ]


# Scenario 6 & 10: DPI 150, 200, 300 dan custom, serta dimensi pixel sesuai DPI
def test_convert_dpi_resolutions_and_dimensions(tmp_path):
    pdf = str(tmp_path / "dpi_test.pdf")
    create_test_pdf(pdf, pages=1)

    # 100 DPI
    dir_100 = str(tmp_path / "out_100")
    ok1, _, data1 = convert_pdf_to_png(pdf, dir_100, pages=[1], dpi=100)
    assert ok1 is True
    with Image.open(data1["generated_files"][0]) as img100:
        w100, h100 = img100.size

    # 200 DPI
    dir_200 = str(tmp_path / "out_200")
    ok2, _, data2 = convert_pdf_to_png(pdf, dir_200, pages=[1], dpi=200)
    assert ok2 is True
    with Image.open(data2["generated_files"][0]) as img200:
        w200, h200 = img200.size

    # Higher DPI must produce proportionally larger pixel dimensions
    assert w200 > w100
    assert h200 > h100
    assert abs((w200 / w100) - 2.0) < 0.05


# Scenario 7: DPI di luar rentang 72–600 ditolak
def test_convert_rejects_invalid_dpi(tmp_path):
    pdf = str(tmp_path / "test.pdf")
    out_dir = str(tmp_path / "out")
    create_test_pdf(pdf, pages=1)

    ok_low, msg_low, _ = convert_pdf_to_png(pdf, out_dir, dpi=50)
    assert ok_low is False
    assert "72 dan 600" in msg_low

    ok_high, msg_high, _ = convert_pdf_to_png(pdf, out_dir, dpi=800)
    assert ok_high is False
    assert "72 dan 600" in msg_high


# Scenario 8: Mode RGB menghasilkan PNG RGB
def test_convert_color_mode_rgb(tmp_path):
    pdf = str(tmp_path / "color_rgb.pdf")
    out_dir = str(tmp_path / "out_rgb")
    create_test_pdf(pdf, pages=1)

    ok, _, data = convert_pdf_to_png(pdf, out_dir, pages=[1], color_mode="rgb")
    assert ok is True
    with Image.open(data["generated_files"][0]) as img:
        assert img.mode in ("RGB", "RGBA")


# Scenario 9: Mode Grayscale menghasilkan PNG Grayscale
def test_convert_color_mode_grayscale(tmp_path):
    pdf = str(tmp_path / "color_gray.pdf")
    out_dir = str(tmp_path / "out_gray")
    create_test_pdf(pdf, pages=1)

    ok, _, data = convert_pdf_to_png(pdf, out_dir, pages=[1], color_mode="grayscale")
    assert ok is True
    with Image.open(data["generated_files"][0]) as img:
        assert img.mode == "L"


# Scenario 11: File bukan PDF, file kosong, atau file rusak ditangani
def test_convert_invalid_corrupt_or_empty_file(tmp_path):
    not_pdf = str(tmp_path / "text.txt")
    with open(not_pdf, "w") as f:
        f.write("Bukan PDF")

    empty_pdf = str(tmp_path / "empty.pdf")
    with open(empty_pdf, "wb") as f:
        pass

    out_dir = str(tmp_path / "out")

    ok1, msg1, _ = convert_pdf_to_png(not_pdf, out_dir)
    assert ok1 is False

    ok2, msg2, _ = convert_pdf_to_png(empty_pdf, out_dir)
    assert ok2 is False


# Scenario 12: PDF terenkripsi mengikuti alur password
def test_convert_encrypted_pdf(tmp_path):
    pdf = str(tmp_path / "locked.pdf")
    out_dir = str(tmp_path / "out_locked")
    pwd = "SecretPassword"
    create_encrypted_pdf(pdf, password=pwd)

    # Without password -> fails
    ok_no_pw, msg_no_pw, _ = convert_pdf_to_png(pdf, out_dir, password=None)
    assert ok_no_pw is False
    assert "password" in msg_no_pw.lower()

    # With correct password -> succeeds
    ok_pw, _, data = convert_pdf_to_png(pdf, out_dir, password=pwd)
    assert ok_pw is True
    assert data["total_success"] == 1


# Scenario 13: Pembatalan proses ditangani dan mempertahankan file yang sudah ada
def test_convert_cancellation_flow(tmp_path):
    pdf = str(tmp_path / "cancel_test.pdf")
    out_dir = str(tmp_path / "out_cancel")
    create_test_pdf(pdf, pages=5)

    call_count = 0

    def cancel_after_two_pages():
        nonlocal call_count
        call_count += 1
        return call_count > 2

    ok, msg, data = convert_pdf_to_png(
        pdf,
        out_dir,
        pages=[1, 2, 3, 4, 5],
        is_cancelled_callback=cancel_after_two_pages,
    )

    assert ok is True
    assert data["is_cancelled"] is True
    assert data["total_success"] == 2
    assert len(data["generated_files"]) == 2
    # Verify the partial files exist on disk
    for f in data["generated_files"]:
        assert os.path.exists(f)


# Scenario 14: File sumber tetap aman
def test_convert_preserves_source_pdf(tmp_path):
    pdf = str(tmp_path / "source.pdf")
    out_dir = str(tmp_path / "out_src")
    create_test_pdf(pdf, pages=2)

    initial_size = os.path.getsize(pdf)
    initial_mtime = os.path.getmtime(pdf)

    ok, _, _ = convert_pdf_to_png(pdf, out_dir)
    assert ok is True

    assert os.path.getsize(pdf) == initial_size
    assert os.path.getmtime(pdf) == initial_mtime


# Output helper functions
def test_get_default_output_dir():
    sample_path = r"C:\Documents\Report.pdf"
    default_dir = get_default_output_dir(sample_path)
    assert default_dir.endswith("Report_png")


def test_get_output_filename_padding():
    # <= 999 pages -> 3-digit padding
    assert get_output_filename("doc", 9, 10) == "doc_page-009.png"
    assert get_output_filename("doc", 15, 100) == "doc_page-015.png"

    # >= 1000 pages -> 4-digit padding
    assert get_output_filename("doc", 9, 1200) == "doc_page-0009.png"

