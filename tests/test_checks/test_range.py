"""Tests for range check."""

import pandas as pd

from pqm.config import RangeEntry
from pqm.checks.range_check import check_range


def test_values_within_range(clean_df):
    ranges = {"amount": RangeEntry(min=0, max=100000)}
    results = check_range(clean_df, ranges)
    assert len(results) == 1
    assert results[0].status == "pass"


def test_values_below_min(clean_df):
    ranges = {"amount": RangeEntry(min=100, max=100000)}
    results = check_range(clean_df, ranges)
    # 45.00 is below 100
    assert results[0].status == "warn"
    assert "below min" in results[0].message


def test_values_above_max(clean_df):
    ranges = {"amount": RangeEntry(min=0, max=1000)}
    results = check_range(clean_df, ranges)
    # 1200.00 is above 1000
    assert results[0].status == "warn"
    assert "above max" in results[0].message


def test_missing_column(clean_df):
    ranges = {"nonexistent": RangeEntry(min=0, max=100)}
    results = check_range(clean_df, ranges)
    assert results[0].status == "warn"
    assert "not found" in results[0].message
