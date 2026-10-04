"""Tests for config loader."""

from pathlib import Path

import pytest

from pqm.config import load_config, PQMConfig


SAMPLE_CONFIG = Path(__file__).parent.parent / "config" / "feeds.yaml"


def test_load_valid_config():
    config = load_config(SAMPLE_CONFIG)
    assert isinstance(config, PQMConfig)
    assert len(config.feeds) == 1
    assert config.feeds[0].name == "sales_csv"
    assert config.feeds[0].type == "csv"


def test_load_config_feed_checks():
    config = load_config(SAMPLE_CONFIG)
    feed = config.feeds[0]
    assert feed.is_check_enabled("schema_drift")
    assert feed.is_check_enabled("null_rate")
    assert feed.is_check_enabled("duplicates")
    assert feed.is_check_enabled("range")
    assert feed.is_check_enabled("row_count")


def test_load_config_null_rate_settings():
    config = load_config(SAMPLE_CONFIG)
    feed = config.feeds[0]
    null_settings = feed.get_null_rate_settings()
    assert null_settings is not None
    assert null_settings.columns["customer_id"] == 0.0
    assert null_settings.columns["email"] == 0.05


def test_load_config_duplicates_settings():
    config = load_config(SAMPLE_CONFIG)
    feed = config.feeds[0]
    dup_settings = feed.get_duplicates_settings()
    assert dup_settings is not None
    assert dup_settings.key == ["order_id"]


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path.yaml")


def test_load_config_invalid_type(tmp_path):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("""
feeds:
  - name: test
    type: parquet
    location: data.parquet
""")
    with pytest.raises(Exception):
        load_config(cfg)
