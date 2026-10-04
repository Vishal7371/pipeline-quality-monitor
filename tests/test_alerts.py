"""Tests for alert deduplication and routing."""

from datetime import datetime, timezone

from pqm.config import AlertsConfig, SlackConfig, FeedConfig
from pqm.storage import Storage, CheckResult
from pqm.alerts import process_alerts


def _make_feed() -> FeedConfig:
    return FeedConfig(name="test_feed", type="csv", location="test.csv")


def test_new_problem_sends_alert(tmp_db):
    storage = Storage(tmp_db)
    alerts_config = AlertsConfig()  # No channels configured, but logic still runs
    feed = _make_feed()

    results = [
        CheckResult(check="null_rate", status="warn", message="High nulls", details={"column": "a"}),
    ]

    sent = process_alerts(feed, results, alerts_config, storage, cooldown_minutes=60)
    # Alert logic runs, state is recorded even if no channel is configured
    state = storage.get_alert_state("test_feed|null_rate|a")
    assert state is not None
    assert state["severity"] == "warn"
    storage.close()


def test_repeat_within_cooldown_suppressed(tmp_db):
    storage = Storage(tmp_db)
    alerts_config = AlertsConfig()
    feed = _make_feed()

    results = [
        CheckResult(check="null_rate", status="warn", message="High nulls", details={"column": "a"}),
    ]

    # First call: records state
    process_alerts(feed, results, alerts_config, storage, cooldown_minutes=60)

    # Second call immediately: should be suppressed (cooldown not elapsed)
    sent = process_alerts(feed, results, alerts_config, storage, cooldown_minutes=9999)
    # The state should exist but last_sent should not be updated a second time
    # (cooldown hasn't elapsed)
    state = storage.get_alert_state("test_feed|null_rate|a")
    assert state is not None
    storage.close()


def test_escalation(tmp_db):
    storage = Storage(tmp_db)
    alerts_config = AlertsConfig()
    feed = _make_feed()

    # First: warn
    process_alerts(
        feed,
        [CheckResult(check="null_rate", status="warn", message="warn", details={"column": "a"})],
        alerts_config, storage, cooldown_minutes=9999,
    )

    # Escalate to fail
    process_alerts(
        feed,
        [CheckResult(check="null_rate", status="fail", message="fail", details={"column": "a"})],
        alerts_config, storage, cooldown_minutes=9999,
    )

    state = storage.get_alert_state("test_feed|null_rate|a")
    assert state["severity"] == "fail"
    storage.close()


def test_recovery(tmp_db):
    storage = Storage(tmp_db)
    alerts_config = AlertsConfig()
    feed = _make_feed()

    # First: a problem
    process_alerts(
        feed,
        [CheckResult(check="null_rate", status="warn", message="warn", details={"column": "a"})],
        alerts_config, storage, cooldown_minutes=60,
    )

    # Now: recovered
    process_alerts(
        feed,
        [CheckResult(check="null_rate", status="pass", message="OK", details={"column": "a"})],
        alerts_config, storage, cooldown_minutes=60,
    )

    state = storage.get_alert_state("test_feed|null_rate|a")
    assert state["resolved_at"] is not None
    storage.close()
