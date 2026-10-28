import os
import pymupdf as fitz
import pytest

from app.services.merge_service import merge_pdfs
from app.utils.validators import validate_pdf_file


def create_dummy_pdf(path: str, num_pages: int, marker: str = "Doc"):
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"{marker} Page {i + 1}")
    doc.save(path)
    doc.close()


def test_merge_two_pdfs(tmp_path):
    pdf1 = str(tmp_path / "doc1.pdf")
    pdf2 = str(tmp_path / "doc2.pdf")
    output_pdf = str(tmp_path / "merged.pdf")

    create_dummy_pdf(pdf1, 2, "First")
    create_dummy_pdf(pdf2, 3, "Second")

    success, msg, total_pages = merge_pdfs([pdf1, pdf2], output_pdf)
    assert success is True
    assert total_pages == 5
    assert os.path.exists(output_pdf)

    # Verify merged document contents & order
    result_doc = fitz.open(output_pdf)
    assert result_doc.page_count == 5
    p1_text = result_doc[0].get_text()
    assert "First Page 1" in p1_text
    p3_text = result_doc[2].get_text()
    assert "Second Page 1" in p3_text
    result_doc.close()


def test_merge_rejects_single_or_empty_input(tmp_path):
    output_pdf = str(tmp_path / "merged.pdf")
    pdf1 = str(tmp_path / "doc1.pdf")
    create_dummy_pdf(pdf1, 2)

    # Empty list
    success, msg, _ = merge_pdfs([], output_pdf)
    assert success is False

    # Single file
    success, msg, _ = merge_pdfs([pdf1], output_pdf)
    assert success is False
    assert "Minimal harus ada dua" in msg


def test_merge_rejects_output_same_as_input(tmp_path):
    pdf1 = str(tmp_path / "doc1.pdf")
    pdf2 = str(tmp_path / "doc2.pdf")
    create_dummy_pdf(pdf1, 2)
    create_dummy_pdf(pdf2, 2)

    success, msg, _ = merge_pdfs([pdf1, pdf2], pdf1)
    assert success is False
    assert "tidak boleh sama" in msg


def test_merge_rejects_invalid_file(tmp_path):
    pdf1 = str(tmp_path / "doc1.pdf")
    invalid_pdf = str(tmp_path / "corrupt.pdf")
    output_pdf = str(tmp_path / "merged.pdf")

    create_dummy_pdf(pdf1, 2)
    with open(invalid_pdf, "w") as f:
        f.write("not a real pdf content")

    success, msg, _ = merge_pdfs([pdf1, invalid_pdf], output_pdf)
    assert success is False
    assert not os.path.exists(output_pdf)
