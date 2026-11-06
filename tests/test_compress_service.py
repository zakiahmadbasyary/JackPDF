import io
import os
from PIL import Image
import pymupdf as fitz
import pytest

from app.services.compress_service import (
    PRESET_CONFIGS,
    calculate_compression_metrics,
    compress_pdf,
)
from app.utils.validators import check_pdf_signatures, validate_output_filename, validate_pdf_file


def create_test_pdf_with_text(path: str, pages: int = 1, text: str = "JackPDF Compress Test") -> None:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)  # A4 standard
        page.insert_text((50, 100), f"{text} - Page {i + 1}")
    doc.save(path)
    doc.close()


def create_test_pdf_with_image(path: str, img_size=(600, 600)) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Create uncompressed raw image
    img = Image.new("RGB", img_size, color=(200, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    page.insert_image(page.rect, stream=buf.getvalue())
    doc.save(path)
    doc.close()


def create_encrypted_pdf(path: str, password: str = "secret123") -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Confidential content")
    doc.save(
        path,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=password,
        owner_pw=password,
    )
    doc.close()


# Scenario 1: PDF teks sederhana berhasil diproses
def test_compress_simple_text_pdf(tmp_path):
    src = str(tmp_path / "simple_text.pdf")
    dst = str(tmp_path / "simple_text_compressed.pdf")
    create_test_pdf_with_text(src, pages=2, text="Halo Dunia")

    success, msg, metrics = compress_pdf(src, dst, preset="balanced")
    assert success is True
    assert os.path.exists(dst)
    assert metrics is not None
    assert metrics["page_count"] == 2
    assert metrics["output_path"] == dst


# Scenario 2: PDF berisi gambar berhasil diproses
def test_compress_image_pdf(tmp_path):
    src = str(tmp_path / "image_heavy.pdf")
    dst = str(tmp_path / "image_heavy_compressed.pdf")
    create_test_pdf_with_image(src, img_size=(800, 800))

    initial_size = os.path.getsize(src)
    success, msg, metrics = compress_pdf(src, dst, preset="small")
    assert success is True
    assert os.path.exists(dst)
    assert metrics["original_size"] == initial_size
    # Image recompression should reduce large PNG image
    assert metrics["compressed_size"] < initial_size
    assert metrics["saved_bytes"] > 0
    assert metrics["change_percent"] > 0


# Scenario 3: PDF multi-halaman mempertahankan jumlah halaman
def test_compress_multipage_preserves_page_count(tmp_path):
    src = str(tmp_path / "multipage.pdf")
    dst = str(tmp_path / "multipage_out.pdf")
    create_test_pdf_with_text(src, pages=7, text="Halaman Multi")

    success, _, metrics = compress_pdf(src, dst, preset="balanced")
    assert success is True

    res_doc = fitz.open(dst)
    assert res_doc.page_count == 7
    res_doc.close()


# Scenario 4: Teks hasil tetap dapat diekstrak
def test_compress_preserves_text_extractability(tmp_path):
    src = str(tmp_path / "selectable.pdf")
    dst = str(tmp_path / "selectable_out.pdf")
    secret_marker = "KunciRahasia12345"
    create_test_pdf_with_text(src, pages=1, text=secret_marker)

    success, _, _ = compress_pdf(src, dst, preset="high")
    assert success is True

    res_doc = fitz.open(dst)
    extracted = res_doc[0].get_text()
    res_doc.close()
    assert secret_marker in extracted


# Scenario 5: Ukuran halaman dan orientasi tetap sama
def test_compress_preserves_dimensions_and_orientation(tmp_path):
    src = str(tmp_path / "dimensions.pdf")
    dst = str(tmp_path / "dimensions_out.pdf")

    doc = fitz.open()
    p1 = doc.new_page(width=400, height=800)  # Custom portrait
    p1.set_rotation(90)
    p1.insert_text((50, 50), "Rotated Page")
    doc.save(src)
    doc.close()

    success, _, _ = compress_pdf(src, dst, preset="balanced")
    assert success is True

    res_doc = fitz.open(dst)
    res_page = res_doc[0]
    assert res_page.rect.width == 800  # Rotated width/height
    assert res_page.rect.height == 400
    assert res_page.rotation == 90
    res_doc.close()


# Scenario 6: File bukan PDF dan file kosong ditolak
def test_compress_rejects_non_pdf_and_empty_file(tmp_path):
    txt_file = str(tmp_path / "document.txt")
    with open(txt_file, "w") as f:
        f.write("Bukan file PDF")

    empty_pdf = str(tmp_path / "empty.pdf")
    with open(empty_pdf, "wb") as f:
        pass  # 0 bytes

    out_file = str(tmp_path / "output.pdf")

    # Non-PDF
    ok1, msg1, _ = compress_pdf(txt_file, out_file)
    assert ok1 is False
    assert "bukan PDF yang valid" in msg1

    # Empty file
    ok2, msg2, _ = compress_pdf(empty_pdf, out_file)
    assert ok2 is False
    assert "kosong" in msg2 or "tidak valid" in msg2


# Scenario 7: PDF rusak ditangani dengan aman
def test_compress_corrupted_pdf_handled_safely(tmp_path):
    corrupt_file = str(tmp_path / "corrupt.pdf")
    with open(corrupt_file, "w") as f:
        f.write("%PDF-1.4 completely corrupted binary junk")

    out_file = str(tmp_path / "out_corrupt.pdf")
    ok, msg, _ = compress_pdf(corrupt_file, out_file)
    assert ok is False
    assert "rusak" in msg.lower() or "gagal" in msg.lower()
    assert not os.path.exists(out_file)


# Scenario 8: PDF terenkripsi mengikuti alur password
def test_compress_encrypted_pdf_password_flow(tmp_path):
    src = str(tmp_path / "locked.pdf")
    dst = str(tmp_path / "unlocked_out.pdf")
    pwd = "MySecretPassword"
    create_encrypted_pdf(src, password=pwd)

    # Without password
    ok_no_pw, msg_no_pw, _ = compress_pdf(src, dst, password=None)
    assert ok_no_pw is False
    assert "password" in msg_no_pw.lower()
    assert not os.path.exists(dst)

    # With wrong password
    ok_wrong, msg_wrong, _ = compress_pdf(src, dst, password="WrongPassword")
    assert ok_wrong is False
    assert "password" in msg_wrong.lower()

    # With correct password
    ok_correct, msg_correct, metrics = compress_pdf(src, dst, password=pwd)
    assert ok_correct is True
    assert os.path.exists(dst)
    assert metrics["page_count"] == 1


# Scenario 9: File sumber tidak berubah
def test_compress_preserves_source_file_intact(tmp_path):
    src = str(tmp_path / "original.pdf")
    dst = str(tmp_path / "out_compressed.pdf")
    create_test_pdf_with_text(src, pages=2, text="Immutable Source")

    initial_src_size = os.path.getsize(src)
    initial_src_mtime = os.path.getmtime(src)

    success, _, _ = compress_pdf(src, dst, preset="balanced")
    assert success is True

    # Check original file unmodified
    assert os.path.getsize(src) == initial_src_size
    assert os.path.getmtime(src) == initial_src_mtime


# Scenario 10: Output tidak menimpa sumber
def test_compress_rejects_output_same_as_source(tmp_path):
    src = str(tmp_path / "same_path.pdf")
    create_test_pdf_with_text(src, pages=1)

    ok, msg, _ = compress_pdf(src, src)
    assert ok is False
    assert "tidak boleh sama" in msg


# Scenario 11: Nama output tidak valid ditolak
def test_compress_rejects_invalid_output_filename(tmp_path):
    src = str(tmp_path / "source.pdf")
    create_test_pdf_with_text(src, pages=1)

    invalid_dst = str(tmp_path / "bad<name>.pdf")
    ok, msg, _ = compress_pdf(src, invalid_dst)
    assert ok is False
    assert "tidak boleh mengandung karakter" in msg


# Scenario 12: Ketiga preset dapat dijalankan
@pytest.mark.parametrize("preset", ["high", "balanced", "small"])
def test_all_three_presets_executable(tmp_path, preset):
    src = str(tmp_path / f"source_{preset}.pdf")
    dst = str(tmp_path / f"output_{preset}.pdf")
    create_test_pdf_with_text(src, pages=2, text=f"Preset {preset}")

    ok, msg, metrics = compress_pdf(src, dst, preset=preset)
    assert ok is True
    assert os.path.exists(dst)
    assert metrics["preset"] == preset

    res_doc = fitz.open(dst)
    assert res_doc.page_count == 2
    res_doc.close()


# Scenario 13: Hasil yang lebih besar ditampilkan dengan jujur
def test_compression_metrics_when_size_increases_or_same():
    # Size reduced
    m_saved = calculate_compression_metrics(1000, 600)
    assert m_saved["saved_bytes"] == 400
    assert m_saved["change_percent"] == 40.0
    assert m_saved["is_larger"] is False
    assert "Hemat" in m_saved["summary_text"]

    # Size increased
    m_larger = calculate_compression_metrics(1000, 1100)
    assert m_larger["saved_bytes"] == -100
    assert m_larger["change_percent"] == -10.0
    assert m_larger["is_larger"] is True
    assert "Ukuran bertambah" in m_larger["summary_text"]
    assert "Hemat" not in m_larger["summary_text"]

    # Size unchanged
    m_same = calculate_compression_metrics(1000, 1000)
    assert m_same["saved_bytes"] == 0
    assert m_same["change_percent"] == 0.0
    assert m_same["is_same"] is True
    assert "tidak berubah" in m_same["summary_text"]


# Scenario 14: Deteksi tanda tangan digital
def test_check_pdf_signatures_detection(tmp_path):
    # Standard PDF without signatures
    pdf_path = str(tmp_path / "unsigned.pdf")
    create_test_pdf_with_text(pdf_path, pages=1)
    assert check_pdf_signatures(pdf_path) is False

    # Non-existent path returns False safely
    assert check_pdf_signatures("non_existent_file.pdf") is False

