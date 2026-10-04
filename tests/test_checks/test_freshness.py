"""Tests for freshness check."""

import time

import pandas as pd

from pqm.config import FeedConfig
from pqm.checks.freshness import check_freshness


def _make_feed(**kwargs) -> FeedConfig:
    defaults = dict(name="test", type="csv", location="test.csv")
    defaults.update(kwargs)
    return FeedConfig(**defaults)


def test_fresh_data():
    feed = _make_feed(freshness_max_age_minutes=60)
    df = pd.DataFrame({"a": [1]})
    results = check_freshness(feed, df, source_mtime=time.time())
    assert results[0].status == "pass"


def test_stale_data():
    feed = _make_feed(freshness_max_age_minutes=60)
    df = pd.DataFrame({"a": [1]})
    old_mtime = time.time() - 7200  # 2 hours ago
    results = check_freshness(feed, df, source_mtime=old_mtime)
    assert results[0].status == "fail"
    assert "minutes old" in results[0].message


def test_no_timestamp_source():
    feed = _make_feed(freshness_max_age_minutes=60)
    df = pd.DataFrame({"a": [1]})
    results = check_freshness(feed, df, source_mtime=None)
    assert results[0].status == "pass"
    assert "skipped" in results[0].message.lower()


def test_no_freshness_configured():
    feed = _make_feed()  # no freshness_max_age_minutes
    df = pd.DataFrame({"a": [1]})
    results = check_freshness(feed, df)
    assert len(results) == 0
