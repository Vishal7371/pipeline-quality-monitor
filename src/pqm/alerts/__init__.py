"""Alert system — deduplicate, format, and send notifications."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pqm.config import AlertsConfig, FeedConfig
from pqm.storage import CheckResult, Storage
from pqm.alerts.slack import send_slack_alert
from pqm.alerts.email_alert import send_email_alert

logger = logging.getLogger(__name__)


def _fingerprint(feed: str, result: CheckResult) -> str:
    """Build a deduplication fingerprint: feed|check|column."""
    column = result.details.get("column", "")
    parts = [feed, result.check]
    if column:
        parts.append(str(column))
    return "|".join(parts)


def process_alerts(
    feed: FeedConfig,
    results: list[CheckResult],
    alerts_config: AlertsConfig,
    storage: Storage,
    cooldown_minutes: int = 60,
) -> int:
    """Send alerts for new, escalated, or recovered problems.

    Deduplication rules:
      - New fingerprint → alert
      - Severity escalation (warn → fail) → alert
      - Cooldown elapsed and problem persists → alert
      - Problem recovered → one "resolved" alert
      - Repeats within cooldown → suppressed

    Returns the number of alerts sent.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    sent_count = 0

    # Separate failures/warnings from passes
    problems = [r for r in results if r.status in ("warn", "fail")]
    passes = [r for r in results if r.status == "pass"]

    # Track current problem fingerprints
    current_fps = set()

    for result in problems:
        fp = _fingerprint(feed.name, result)
        current_fps.add(fp)

        state = storage.get_alert_state(fp)

        should_alert = False
        reason = ""

        if state is None:
            # New problem
            should_alert = True
            reason = "new"
            storage.upsert_alert_state(fp, result.status, now_iso, now_iso)

        elif state.get("resolved_at"):
            # Was resolved, now back
            should_alert = True
            reason = "recurrence"
            storage.upsert_alert_state(fp, result.status, now_iso, now_iso)

        elif state["severity"] == "warn" and result.status == "fail":
            # Escalation
            should_alert = True
            reason = "escalation"
            storage.upsert_alert_state(fp, result.status, state["first_seen"], now_iso)

        else:
            # Check cooldown
            last_sent = state.get("last_sent")
            if last_sent:
                last_dt = datetime.fromisoformat(last_sent)
                elapsed = (now - last_dt).total_seconds() / 60.0
                if elapsed >= cooldown_minutes:
                    should_alert = True
                    reason = "cooldown_elapsed"
                    storage.upsert_alert_state(
                        fp, result.status, state["first_seen"], now_iso
                    )

        if should_alert:
            _send(feed.name, result, reason, alerts_config)
            sent_count += 1

    # Check for recoveries: previously failing fingerprints that now pass
    for result in passes:
        fp = _fingerprint(feed.name, result)
        state = storage.get_alert_state(fp)
        if state and not state.get("resolved_at"):
            # Problem resolved
            recovery = CheckResult(
                check=result.check,
                status="pass",
                message=f"RESOLVED: {result.message}",
                details={**result.details, "resolved": True},
            )
            _send(feed.name, recovery, "resolved", alerts_config)
            storage.upsert_alert_state(
                fp, "pass", state["first_seen"], now_iso, resolved_at=now_iso
            )
            sent_count += 1

    return sent_count


def _send(
    feed_name: str,
    result: CheckResult,
    reason: str,
    alerts_config: AlertsConfig,
) -> None:
    """Dispatch an alert to configured channels based on severity."""
    logger.info(
        "Alert [%s] %s: %s (%s)", result.status.upper(), feed_name, result.message, reason
    )

    # Slack: all severities
    if alerts_config.slack:
        try:
            send_slack_alert(feed_name, result, alerts_config.slack)
        except Exception as e:
            logger.error("Failed to send Slack alert: %s", e)

    # Email: fail severity only (unless resolved)
    if alerts_config.email and result.status in ("fail", "pass"):
        try:
            send_email_alert(feed_name, result, alerts_config.email)
        except Exception as e:
            logger.error("Failed to send email alert: %s", e)
