"""Check engine — run enabled checks and collect results."""

from __future__ import annotations

from typing import Any

import pandas as pd

from pqm.config import FeedConfig
from pqm.profile import Profile
from pqm.storage import CheckResult, Storage

from pqm.checks.schema_drift import check_schema_drift
from pqm.checks.null_rate import check_null_rate
from pqm.checks.duplicates import check_duplicates
from pqm.checks.range_check import check_range
from pqm.checks.row_count import check_row_count
from pqm.checks.freshness import check_freshness


def run_checks(
    feed: FeedConfig,
    df: pd.DataFrame,
    current_profile: Profile,
    baseline: Profile | None,
    storage: Storage,
    source_mtime: float | None = None,
) -> list[CheckResult]:
    """Run all enabled checks for a feed and return structured results."""
    results: list[CheckResult] = []

    # Schema drift — always run if a baseline exists
    if baseline is not None:
        drift_results = check_schema_drift(current_profile, baseline)
        results.extend(drift_results)

    # Skip per-column checks on empty batches to avoid noise
    if len(df) == 0:
        results.append(CheckResult(
            check="row_count",
            status="fail",
            message="Batch is empty (0 rows)",
            details={"row_count": 0},
        ))
        return results

    # Null rate
    if feed.is_check_enabled("null_rate"):
        settings = feed.get_null_rate_settings()
        if settings:
            results.extend(check_null_rate(df, settings))

    # Duplicates
    if feed.is_check_enabled("duplicates"):
        settings = feed.get_duplicates_settings()
        if settings:
            results.extend(check_duplicates(df, settings))

    # Range
    if feed.is_check_enabled("range"):
        range_settings = feed.get_range_settings()
        if range_settings:
            results.extend(check_range(df, range_settings))

    # Row count
    if feed.is_check_enabled("row_count"):
        rc_settings = feed.get_row_count_settings()
        recent_counts = storage.get_recent_row_counts(feed.name, rc_settings.window_runs)
        results.extend(check_row_count(current_profile.row_count, recent_counts, rc_settings))

    # Freshness
    if feed.freshness_max_age_minutes is not None:
        results.extend(check_freshness(
            feed=feed,
            df=df,
            source_mtime=source_mtime,
        ))

    return results
