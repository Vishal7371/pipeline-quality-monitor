"""Tests for duplicates check."""

from pathlib import Path

import pandas as pd

from pqm.config import DuplicatesSettings
from pqm.checks.duplicates import check_duplicates


DATA_DIR = Path(__file__).parent.parent / "data"


def test_no_duplicates(clean_df):
    settings = DuplicatesSettings(key=["order_id"])
    results = check_duplicates(clean_df, settings)
    assert len(results) == 1
    assert results[0].status == "pass"


def test_has_duplicates():
    df = pd.read_csv(DATA_DIR / "duplicated_keys.csv")
    settings = DuplicatesSettings(key=["order_id"])
    results = check_duplicates(df, settings)
    assert len(results) == 1
    assert results[0].status == "fail"
    assert results[0].details["duplicate_count"] == 4  # 2 pairs = 4 rows


def test_missing_key_column(clean_df):
    settings = DuplicatesSettings(key=["nonexistent_col"])
    results = check_duplicates(clean_df, settings)
    assert len(results) == 1
    assert results[0].status == "fail"
    assert "missing" in results[0].message.lower()
