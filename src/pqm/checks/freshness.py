"""Freshness check — detect stale data."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd

from pqm.config import FeedConfig
from pqm.storage import CheckResult


def check_freshness(
    feed: FeedConfig,
    df: pd.DataFrame,
    source_mtime: float | None = None,
) -> list[CheckResult]:
    """Check whether the data source is fresh enough.

    For CSV: uses file modification time (source_mtime).
    For SQL: uses max(freshness_column) if configured.
    If neither is available, the check is skipped.
    """
    max_age = feed.freshness_max_age_minutes
    if max_age is None:
        return []

    now = time.time()
    data_time: float | None = None
    method = ""

    # Try freshness_column first (works for both CSV and SQL)
    if feed.freshness_column and feed.freshness_column in df.columns:
        col = df[feed.freshness_column].dropna()
        if len(col) > 0:
            try:
                max_val = pd.to_datetime(col).max()
                if pd.notna(max_val):
                    # Convert to unix timestamp
                    if max_val.tzinfo is None:
                        max_val = max_val.tz_localize("UTC")
                    data_time = max_val.timestamp()
                    method = f"freshness_column '{feed.freshness_column}'"
            except Exception:
                pass

    # Fall back to file mtime for CSV
    if data_time is None and source_mtime is not None:
        data_time = source_mtime
        method = "file modification time"

    if data_time is None:
        return [CheckResult(
            check="freshness",
            status="pass",
            message="Freshness check skipped: no timestamp source available",
            details={"reason": "no_timestamp_source"},
        )]

    age_minutes = (now - data_time) / 60.0

    if age_minutes > max_age:
        return [CheckResult(
            check="freshness",
            status="fail",
            message=(
                f"Data is {age_minutes:.0f} minutes old "
                f"(limit: {max_age} minutes, via {method})"
            ),
            details={
                "age_minutes": round(age_minutes, 1),
                "max_age_minutes": max_age,
                "method": method,
                "data_timestamp": datetime.fromtimestamp(data_time, tz=timezone.utc).isoformat(),
            },
        )]

    return [CheckResult(
        check="freshness",
        status="pass",
        message=f"Data is {age_minutes:.0f} minutes old (limit: {max_age}, via {method})",
        details={
            "age_minutes": round(age_minutes, 1),
            "max_age_minutes": max_age,
            "method": method,
        },
    )]
