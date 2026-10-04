"""Duplicates check — detect rows that share the same key."""

from __future__ import annotations

import pandas as pd

from pqm.config import DuplicatesSettings
from pqm.storage import CheckResult


def check_duplicates(df: pd.DataFrame, settings: DuplicatesSettings) -> list[CheckResult]:
    """Check for duplicate rows based on the configured key columns.

    Returns a single CheckResult: fail if duplicates found, pass otherwise.
    """
    missing = [c for c in settings.key if c not in df.columns]
    if missing:
        return [CheckResult(
            check="duplicates",
            status="fail",
            message=f"Key columns missing from data: {missing}",
            details={"missing_columns": missing, "key": settings.key},
        )]

    duplicated_mask = df.duplicated(subset=settings.key, keep=False)
    dup_count = int(duplicated_mask.sum())

    if dup_count > 0:
        # Grab a few example duplicate keys for the details
        dup_rows = df[duplicated_mask].head(5)
        examples = dup_rows[settings.key].to_dict(orient="records")

        return [CheckResult(
            check="duplicates",
            status="fail",
            message=f"{dup_count} duplicate rows on key {settings.key}",
            details={
                "key": settings.key,
                "duplicate_count": dup_count,
                "examples": examples,
            },
        )]

    return [CheckResult(
        check="duplicates",
        status="pass",
        message=f"No duplicates on key {settings.key}",
        details={"key": settings.key, "duplicate_count": 0},
    )]
