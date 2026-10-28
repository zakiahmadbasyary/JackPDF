import os
import pymupdf as fitz
import pytest

from app.services.split_service import (
    split_pdf_by_range,
    split_pdf_each_page,
    split_pdf_fixed_size,
)
from app.utils.validators import parse_page_range


def create_dummy_pdf(path: str, num_pages: int):
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i + 1} Content")
    doc.save(path)
    doc.close()


def test_split_by_range_continuous(tmp_path):
    src_pdf = str(tmp_path / "sample.pdf")
    out_pdf = str(tmp_path / "extracted_1_3.pdf")
    create_dummy_pdf(src_pdf, 5)

    success, msg, files = split_pdf_by_range(src_pdf, "1-3", out_pdf)
    assert success is True
    assert len(files) == 1
    assert os.path.exists(out_pdf)

    res = fitz.open(out_pdf)
    assert res.page_count == 3
    assert "Page 1 Content" in res[0].get_text()
    assert "Page 2 Content" in res[1].get_text()
    assert "Page 3 Content" in res[2].get_text()
    res.close()


def test_split_by_range_discrete(tmp_path):
    src_pdf = str(tmp_path / "sample.pdf")
    out_pdf = str(tmp_path / "extracted_1_3_5.pdf")
    create_dummy_pdf(src_pdf, 6)

    success, msg, files = split_pdf_by_range(src_pdf, "1,3,5", out_pdf)
    assert success is True
    assert len(files) == 1

    res = fitz.open(out_pdf)
    assert res.page_count == 3
    assert "Page 1 Content" in res[0].get_text()
    assert "Page 3 Content" in res[1].get_text()
    assert "Page 5 Content" in res[2].get_text()
    res.close()


def test_split_each_page(tmp_path):
    src_pdf = str(tmp_path / "sample.pdf")
    out_dir = str(tmp_path / "pages_output")
    create_dummy_pdf(src_pdf, 4)

    success, msg, files = split_pdf_each_page(src_pdf, out_dir)
    assert success is True
    assert len(files) == 4
    for idx, fpath in enumerate(files):
        assert os.path.exists(fpath)
        d = fitz.open(fpath)
        assert d.page_count == 1
        assert f"Page {idx + 1} Content" in d[0].get_text()
        d.close()


def test_split_fixed_size(tmp_path):
    src_pdf = str(tmp_path / "sample.pdf")
    out_dir = str(tmp_path / "parts_output")
    create_dummy_pdf(src_pdf, 5)

    # 5 pages into chunks of 2: part1 (2), part2 (2), part3 (1)
    success, msg, files = split_pdf_fixed_size(src_pdf, out_dir, pages_per_file=2)
    assert success is True
    assert len(files) == 3

    d1 = fitz.open(files[0])
    assert d1.page_count == 2
    d1.close()

    d3 = fitz.open(files[2])
    assert d3.page_count == 1
    d3.close()


def test_parse_page_range_validation():
    # Valid ranges
    ok, pages, err = parse_page_range("1-3, 5, 8-10", 10)
    assert ok is True
    assert pages == [1, 2, 3, 5, 8, 9, 10]

    # Zero rejection
    ok, _, err = parse_page_range("0, 1, 2", 10)
    assert ok is False
    assert "0" in err

    # Reverse range rejection
    ok, _, err = parse_page_range("5-2", 10)
    assert ok is False
    assert "terbalik" in err

    # Out of bounds rejection
    ok, _, err = parse_page_range("1-15", 10)
    assert ok is False
    assert "melebihi" in err

    # Duplicate rejection
    ok, _, err = parse_page_range("1, 2, 2, 3", 10)
    assert ok is False
    assert "duplikat" in err

    # Malformed rejection
    ok, _, err = parse_page_range("1--3", 10)
    assert ok is False

    ok, _, err = parse_page_range("a-b", 10)
    assert ok is False

    ok, _, err = parse_page_range("", 10)
    assert ok is False
