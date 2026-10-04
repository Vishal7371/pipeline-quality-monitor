"""Tests for the profiler."""

import pandas as pd

from pqm.profile import build_profile, normalise_type, Profile


def test_normalise_type_known():
    assert normalise_type("int64") == "int"
    assert normalise_type("float64") == "float"
    assert normalise_type("object") == "string"
    assert normalise_type("bool") == "bool"
    assert normalise_type("datetime64[ns]") == "datetime"


def test_normalise_type_unknown():
    assert normalise_type("complex128") == "string"


def test_build_profile_basic(clean_df):
    profile = build_profile(clean_df)
    assert profile.row_count == 5
    assert "order_id" in profile.schema
    assert "email" in profile.schema
    assert profile.schema["order_id"] == "int"
    assert profile.schema["email"] == "string"


def test_build_profile_null_rates(clean_df):
    profile = build_profile(clean_df)
    # Clean data should have zero nulls
    for col, rate in profile.null_rates.items():
        assert rate == 0.0, f"Expected 0 nulls for {col}, got {rate}"


def test_build_profile_numeric_ranges(clean_df):
    profile = build_profile(clean_df)
    assert "amount" in profile.min_values
    assert "amount" in profile.max_values
    assert profile.min_values["amount"] == 45.0
    assert profile.max_values["amount"] == 1200.0


def test_build_profile_empty():
    df = pd.DataFrame(columns=["a", "b", "c"])
    profile = build_profile(df)
    assert profile.row_count == 0
    assert len(profile.schema) == 3


def test_profile_serialization(clean_df):
    profile = build_profile(clean_df)
    d = profile.to_dict()
    restored = Profile.from_dict(d)
    assert restored.schema == profile.schema
    assert restored.row_count == profile.row_count
    assert restored.null_rates == profile.null_rates
