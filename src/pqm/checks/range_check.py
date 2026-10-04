"""Range check — flag values outside min/max bounds."""

from __future__ import annotations

import pandas as pd

from pqm.config import RangeEntry
from pqm.storage import CheckResult


def check_range(
    df: pd.DataFrame,
    ranges: dict[str, RangeEntry],
) -> list[CheckResult]:
    """Check that numeric column values fall within configured min/max bounds.

    Returns one CheckResult per column.
    """
    results: list[CheckResult] = []

    for col, bounds in ranges.items():
        if col not in df.columns:
            results.append(CheckResult(
                check="range",
                status="warn",
                message=f"Column '{col}' not found in data (skipping range check)",
                details={"column": col, "reason": "missing_column"},
            ))
            continue

        series = df[col].dropna()

        if len(series) == 0:
            results.append(CheckResult(
                check="range",
                status="pass",
                message=f"Column '{col}' has no non-null values to check",
                details={"column": col},
            ))
            continue

        violations: list[str] = []
        detail: dict = {"column": col}

        actual_min = float(series.min())
        actual_max = float(series.max())
        detail["actual_min"] = actual_min
        detail["actual_max"] = actual_max

        if bounds.min is not None:
            below = int((series < bounds.min).sum())
            detail["below_min_count"] = below
            if below > 0:
                violations.append(f"{below} values below min {bounds.min}")

        if bounds.max is not None:
            above = int((series > bounds.max).sum())
            detail["above_max_count"] = above
            if above > 0:
                violations.append(f"{above} values above max {bounds.max}")

        if violations:
            results.append(CheckResult(
                check="range",
                status="warn",
                message=f"Range violation in '{col}': {'; '.join(violations)}",
                details=detail,
            ))
        else:
            results.append(CheckResult(
                check="range",
                status="pass",
                message=f"Column '{col}' values within range [{bounds.min}, {bounds.max}]",
                details=detail,
            ))

    return results
