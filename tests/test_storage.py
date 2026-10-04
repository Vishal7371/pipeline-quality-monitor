"""Tests for the storage module."""

from datetime import datetime, timezone

from pqm.storage import Storage, Run, CheckResult


def test_save_and_load_run(storage):
    run = Run(
        id=None,
        feed="test_feed",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        row_count=100,
        status="pass",
        results=[
            CheckResult(check="null_rate", status="pass", message="OK", details={"col": "a"}),
        ],
    )
    run_id = storage.save_run(run)
    assert run_id > 0

    runs = storage.get_recent_runs("test_feed")
    assert len(runs) == 1
    assert runs[0].feed == "test_feed"
    assert runs[0].status == "pass"
    assert len(runs[0].results) == 1


def test_get_recent_row_counts(storage):
    for i in range(5):
        run = Run(
            id=None,
            feed="feed_a",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            row_count=100 + i,
            status="pass",
        )
        storage.save_run(run)

    counts = storage.get_recent_row_counts("feed_a", window=3)
    assert len(counts) == 3


def test_alert_state(storage):
    fp = "feed|check|col"
    assert storage.get_alert_state(fp) is None

    storage.upsert_alert_state(fp, "warn", "2026-01-01T00:00:00")
    state = storage.get_alert_state(fp)
    assert state is not None
    assert state["severity"] == "warn"

    # Update severity
    storage.upsert_alert_state(fp, "fail", "2026-01-01T00:00:00", "2026-01-02T00:00:00")
    state = storage.get_alert_state(fp)
    assert state["severity"] == "fail"


def test_prune(storage):
    run = Run(
        id=None,
        feed="old_feed",
        started_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        finished_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        row_count=50,
        status="pass",
    )
    storage.save_run(run)

    deleted = storage.prune(days=1)
    assert deleted == 1

    runs = storage.get_recent_runs("old_feed")
    assert len(runs) == 0
