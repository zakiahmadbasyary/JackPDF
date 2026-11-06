import pytest
from app.services.convert_png_service import format_page_selection, parse_page_selection


def test_parse_valid_single_and_ranges():
    ok, pages, err = parse_page_selection("1, 3, 6-8, 12", 15)
    assert ok is True
    assert pages == [1, 3, 6, 7, 8, 12]
    assert err == ""


def test_parse_single_page():
    ok, pages, _ = parse_page_selection("5", 10)
    assert ok is True
    assert pages == [5]


def test_parse_full_continuous_range():
    ok, pages, _ = parse_page_selection("1-5", 5)
    assert ok is True
    assert pages == [1, 2, 3, 4, 5]


def test_parse_deduplication_and_sorting():
    # Input has duplicate pages and unsorted order
    ok, pages, _ = parse_page_selection("7, 2, 1-3, 2, 7", 10)
    assert ok is True
    assert pages == [1, 2, 3, 7]


def test_parse_ignores_spaces():
    ok, pages, _ = parse_page_selection("  2 ,  5 - 7  ,  9  ", 10)
    assert ok is True
    assert pages == [2, 5, 6, 7, 9]


def test_parse_rejects_empty():
    ok, pages, err = parse_page_selection("", 10)
    assert ok is False
    assert pages == []
    assert "kosong" in err.lower()

    ok2, _, _ = parse_page_selection("   ", 10)
    assert ok2 is False


def test_parse_rejects_non_numeric():
    ok, _, err = parse_page_selection("1, 2, abc, 5", 10)
    assert ok is False
    assert "tidak valid" in err.lower()


def test_parse_rejects_reverse_range():
    ok, _, err = parse_page_selection("5-2", 10)
    assert ok is False
    assert "terbalik" in err.lower()


def test_parse_rejects_zero_or_negative():
    ok, _, err = parse_page_selection("0, 1, 2", 10)
    assert ok is False
    assert "dimulai dari 1" in err.lower()


def test_parse_rejects_page_exceeding_total():
    ok, _, err = parse_page_selection("1, 4, 11", 10)
    assert ok is False
    assert "melebihi" in err.lower()


def test_parse_rejects_range_exceeding_total():
    ok, _, err = parse_page_selection("1, 8-15", 10)
    assert ok is False
    assert "melebihi" in err.lower()


def test_parse_rejects_empty_comma_tokens():
    ok, _, err = parse_page_selection("1,,2", 10)
    assert ok is False
    assert "koma" in err.lower()


def test_format_page_selection_compact():
    assert format_page_selection([1, 2, 3, 5, 7, 8, 9]) == "1-3, 5, 7-9"
    assert format_page_selection([2, 5, 9]) == "2, 5, 9"
    assert format_page_selection([1]) == "1"
    assert format_page_selection([1, 2, 3, 4]) == "1-4"
    assert format_page_selection([]) == ""

