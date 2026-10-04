"""Tests for row count check."""

from pqm.config import RowCountSettings
from pqm.checks.row_count import check_row_count


def test_not_enough_history():
    results = check_row_count(100, [100, 99], RowCountSettings())
    assert results[0].status == "pass"
    assert "not enough history" in results[0].message


def test_within_tolerance():
    results = check_row_count(100, [95, 105, 100, 98], RowCountSettings(tolerance_pct=40))
    assert results[0].status == "pass"


def test_exceeds_tolerance():
    results = check_row_count(10, [100, 100, 100, 100], RowCountSettings(tolerance_pct=40))
    assert results[0].status == "warn"
    assert "deviates" in results[0].message


def test_zero_average():
    results = check_row_count(0, [0, 0, 0], RowCountSettings())
    assert results[0].status == "pass"
