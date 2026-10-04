"""Tests for schema drift check."""

from pathlib import Path

import pandas as pd

from pqm.profile import build_profile
from pqm.checks.schema_drift import check_schema_drift


DATA_DIR = Path(__file__).parent.parent / "data"


def test_no_drift(clean_profile):
    """Same schema → no results."""
    results = check_schema_drift(clean_profile, clean_profile)
    assert len(results) == 0


def test_column_removed(clean_profile):
    df = pd.read_csv(DATA_DIR / "column_removed.csv")
    current = build_profile(df)
    results = check_schema_drift(current, clean_profile)

    removed = [r for r in results if r.check == "schema_drift:column_removed"]
    assert len(removed) == 1
    assert removed[0].status == "fail"
    assert "customer_id" in removed[0].message


def test_column_added(clean_profile):
    df = pd.read_csv(DATA_DIR / "clean.csv")
    df["new_col"] = "value"
    current = build_profile(df)
    results = check_schema_drift(current, clean_profile)

    added = [r for r in results if r.check == "schema_drift:column_added"]
    assert len(added) == 1
    assert added[0].status == "warn"
    assert "new_col" in added[0].message


def test_type_changed(clean_profile):
    df = pd.read_csv(DATA_DIR / "retyped_column.csv")
    current = build_profile(df)
    results = check_schema_drift(current, clean_profile)

    type_changes = [r for r in results if r.check == "schema_drift:type_changed"]
    assert len(type_changes) == 1
    assert type_changes[0].status == "fail"
    assert "customer_id" in type_changes[0].message


def test_rename_detection(clean_profile):
    """Rename: remove 'customer_id' and add 'cust_id' with same type."""
    df = pd.read_csv(DATA_DIR / "clean.csv")
    df = df.rename(columns={"customer_id": "cust_id"})
    current = build_profile(df)
    results = check_schema_drift(current, clean_profile)

    removed = [r for r in results if r.check == "schema_drift:column_removed"]
    assert len(removed) == 1
    assert "possible rename" in removed[0].message.lower()
