"""Schema drift check — detect columns added, removed, or retyped."""

from __future__ import annotations

from difflib import SequenceMatcher

from pqm.profile import Profile
from pqm.storage import CheckResult


def _similar_names(a: str, b: str, threshold: float = 0.6) -> bool:
    """Return True if two column names are similar enough to suggest a rename."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


def check_schema_drift(current: Profile, baseline: Profile) -> list[CheckResult]:
    """Compare current schema against baseline and report drift.

    Returns one CheckResult per detected issue:
      - column_removed  -> fail
      - column_added    -> warn
      - type_changed    -> fail
    """
    results: list[CheckResult] = []

    baseline_cols = set(baseline.schema.keys())
    current_cols = set(current.schema.keys())

    removed = baseline_cols - current_cols
    added = current_cols - baseline_cols

    # Detect possible renames: a removed + added pair with same type and similar name
    possible_renames: list[tuple[str, str]] = []
    unmatched_removed = set(removed)
    unmatched_added = set(added)

    for rem_col in removed:
        rem_type = baseline.schema[rem_col]
        for add_col in added:
            add_type = current.schema[add_col]
            if rem_type == add_type and _similar_names(rem_col, add_col):
                possible_renames.append((rem_col, add_col))
                unmatched_removed.discard(rem_col)
                unmatched_added.discard(add_col)
                break

    # Report removed columns
    for col in removed:
        rename_hint = ""
        for old, new in possible_renames:
            if old == col:
                rename_hint = f" (possible rename to '{new}')"
                break

        results.append(CheckResult(
            check="schema_drift:column_removed",
            status="fail",
            message=f"Column removed: {col}{rename_hint}",
            details={"column": col, "type": baseline.schema[col], "rename_hint": rename_hint.strip()},
        ))

    # Report added columns
    for col in added:
        rename_hint = ""
        for old, new in possible_renames:
            if new == col:
                rename_hint = f" (possible rename from '{old}')"
                break

        results.append(CheckResult(
            check="schema_drift:column_added",
            status="warn",
            message=f"Column added: {col}{rename_hint}",
            details={"column": col, "type": current.schema[col], "rename_hint": rename_hint.strip()},
        ))

    # Report type changes on columns present in both
    for col in baseline_cols & current_cols:
        old_type = baseline.schema[col]
        new_type = current.schema[col]
        if old_type != new_type:
            results.append(CheckResult(
                check="schema_drift:type_changed",
                status="fail",
                message=f"Type changed for '{col}': {old_type} -> {new_type}",
                details={"column": col, "old_type": old_type, "new_type": new_type},
            ))

    return results
