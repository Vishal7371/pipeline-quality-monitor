"""Row count check — detect unexpected volume changes."""

from __future__ import annotations

import statistics

from pqm.config import RowCountSettings
from pqm.storage import CheckResult


def check_row_count(
    current_count: int,
    recent_counts: list[int],
    settings: RowCountSettings,
) -> list[CheckResult]:
    """Compare current row count against the recent average.

    Needs at least 3 prior runs; before that, reports pass with a note.
    """
    if len(recent_counts) < 3:
        return [CheckResult(
            check="row_count",
            status="pass",
            message=f"Row count: {current_count} (not enough history yet, need 3 runs, have {len(recent_counts)})",
            details={
                "row_count": current_count,
                "history_size": len(recent_counts),
                "minimum_required": 3,
            },
        )]

    avg = statistics.mean(recent_counts)
    if avg == 0:
        # Avoid division by zero
        return [CheckResult(
            check="row_count",
            status="pass",
            message=f"Row count: {current_count} (historical average is 0)",
            details={"row_count": current_count, "average": 0},
        )]

    deviation_pct = abs(current_count - avg) / avg * 100

    if deviation_pct > settings.tolerance_pct:
        return [CheckResult(
            check="row_count",
            status="warn",
            message=(
                f"Row count {current_count} deviates {deviation_pct:.1f}% "
                f"from recent average {avg:.0f} (tolerance: {settings.tolerance_pct}%)"
            ),
            details={
                "row_count": current_count,
                "average": round(avg, 2),
                "deviation_pct": round(deviation_pct, 2),
                "tolerance_pct": settings.tolerance_pct,
                "window": len(recent_counts),
            },
        )]

    return [CheckResult(
        check="row_count",
        status="pass",
        message=f"Row count {current_count} within {deviation_pct:.1f}% of average {avg:.0f}",
        details={
            "row_count": current_count,
            "average": round(avg, 2),
            "deviation_pct": round(deviation_pct, 2),
            "tolerance_pct": settings.tolerance_pct,
        },
    )]
