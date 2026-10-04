"""Null rate check — flag columns with too many nulls."""

from __future__ import annotations

import pandas as pd

from pqm.config import NullRateSettings
from pqm.storage import CheckResult


def check_null_rate(df: pd.DataFrame, settings: NullRateSettings) -> list[CheckResult]:
    """Check each configured column's null rate against its threshold.

    Returns one CheckResult per column (pass or warn).
    """
    results: list[CheckResult] = []

    for col, max_share in settings.columns.items():
        if col not in df.columns:
            results.append(CheckResult(
                check="null_rate",
                status="warn",
                message=f"Column '{col}' not found in data (skipping null check)",
                details={"column": col, "reason": "missing_column"},
            ))
            continue

        actual = float(df[col].isna().mean())

        if actual > max_share:
            results.append(CheckResult(
                check="null_rate",
                status="warn",
                message=f"Null rate for '{col}': {actual:.2%} exceeds limit {max_share:.2%}",
                details={
                    "column": col,
                    "actual_null_rate": round(actual, 4),
                    "max_allowed": max_share,
                },
            ))
        else:
            results.append(CheckResult(
                check="null_rate",
                status="pass",
                message=f"Null rate for '{col}': {actual:.2%} within limit {max_share:.2%}",
                details={
                    "column": col,
                    "actual_null_rate": round(actual, 4),
                    "max_allowed": max_share,
                },
            ))

    return results
