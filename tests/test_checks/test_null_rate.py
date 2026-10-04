"""Tests for null rate check."""

from pathlib import Path

import pandas as pd

from pqm.config import NullRateSettings
from pqm.checks.null_rate import check_null_rate


DATA_DIR = Path(__file__).parent.parent / "data"


def test_clean_data_passes(clean_df):
    settings = NullRateSettings(columns={"customer_id": 0.0, "email": 0.05})
    results = check_null_rate(clean_df, settings)
    assert all(r.status == "pass" for r in results)


def test_null_spike_fails():
    df = pd.read_csv(DATA_DIR / "null_spike.csv")
    settings = NullRateSettings(columns={"customer_id": 0.0, "email": 0.05})
    results = check_null_rate(df, settings)

    failing = [r for r in results if r.status == "warn"]
    assert len(failing) == 2  # both customer_id and email exceed thresholds


def test_missing_column(clean_df):
    settings = NullRateSettings(columns={"nonexistent": 0.0})
    results = check_null_rate(clean_df, settings)
    assert len(results) == 1
    assert results[0].status == "warn"
    assert "not found" in results[0].message
