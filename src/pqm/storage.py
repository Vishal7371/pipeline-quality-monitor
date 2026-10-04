"""Run-history storage — persist runs and check results in SQLite."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Literal


@dataclass
class CheckResult:
    """Output of a single check."""

    check: str
    status: Literal["pass", "warn", "fail"]
    message: str
    details: dict


@dataclass
class Run:
    """One execution of PQM against a feed."""

    id: int | None
    feed: str
    started_at: datetime
    finished_at: datetime | None
    row_count: int | None
    status: Literal["pass", "warn", "fail", "error", "baseline_created"]
    results: list[CheckResult] = field(default_factory=list)


class Storage:
    """SQLite-backed run history."""

    DDL = """
    CREATE TABLE IF NOT EXISTS runs (
        id          INTEGER PRIMARY KEY,
        feed        TEXT NOT NULL,
        started_at  TEXT NOT NULL,
        finished_at TEXT,
        row_count   INTEGER,
        status      TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS check_results (
        id          INTEGER PRIMARY KEY,
        run_id      INTEGER NOT NULL REFERENCES runs(id),
        check_name  TEXT NOT NULL,
        status      TEXT NOT NULL,
        message     TEXT,
        details     TEXT
    );

    CREATE TABLE IF NOT EXISTS baselines (
        feed       TEXT PRIMARY KEY,
        profile    TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS alert_state (
        fingerprint TEXT PRIMARY KEY,
        severity    TEXT NOT NULL,
        first_seen  TEXT NOT NULL,
        last_sent   TEXT,
        resolved_at TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_runs_feed_time ON runs(feed, started_at);
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.executescript(self.DDL)
        self._conn.commit()

    def save_run(self, run: Run) -> int:
        """Insert a run and its check_results. Return the run id."""
        cursor = self._conn.execute(
            """INSERT INTO runs (feed, started_at, finished_at, row_count, status)
               VALUES (?, ?, ?, ?, ?)""",
            (
                run.feed,
                run.started_at.isoformat(),
                run.finished_at.isoformat() if run.finished_at else None,
                run.row_count,
                run.status,
            ),
        )
        run_id = cursor.lastrowid
        assert run_id is not None

        for result in run.results:
            self._conn.execute(
                """INSERT INTO check_results (run_id, check_name, status, message, details)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    run_id,
                    result.check,
                    result.status,
                    result.message,
                    json.dumps(result.details),
                ),
            )

        self._conn.commit()
        run.id = run_id
        return run_id

    def get_recent_runs(self, feed: str | None = None, limit: int = 20) -> list[Run]:
        """Return the most recent runs, newest first."""
        if feed:
            rows = self._conn.execute(
                """SELECT id, feed, started_at, finished_at, row_count, status
                   FROM runs WHERE feed = ?
                   ORDER BY started_at DESC LIMIT ?""",
                (feed, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT id, feed, started_at, finished_at, row_count, status
                   FROM runs ORDER BY started_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()

        runs: list[Run] = []
        for row in rows:
            run_id, feed_name, started, finished, rc, status = row

            # Load check results for this run
            result_rows = self._conn.execute(
                """SELECT check_name, status, message, details
                   FROM check_results WHERE run_id = ?""",
                (run_id,),
            ).fetchall()

            results = [
                CheckResult(
                    check=r[0],
                    status=r[1],
                    message=r[2] or "",
                    details=json.loads(r[3]) if r[3] else {},
                )
                for r in result_rows
            ]

            runs.append(Run(
                id=run_id,
                feed=feed_name,
                started_at=datetime.fromisoformat(started),
                finished_at=datetime.fromisoformat(finished) if finished else None,
                row_count=rc,
                status=status,
                results=results,
            ))

        return runs

    def get_recent_row_counts(self, feed: str, window: int = 10) -> list[int]:
        """Return the last *window* row counts for a feed."""
        rows = self._conn.execute(
            """SELECT row_count FROM runs
               WHERE feed = ? AND row_count IS NOT NULL AND status != 'error'
               ORDER BY started_at DESC LIMIT ?""",
            (feed, window),
        ).fetchall()
        return [r[0] for r in rows]

    def get_alert_state(self, fingerprint: str) -> dict | None:
        """Load alert state for a fingerprint."""
        row = self._conn.execute(
            "SELECT severity, first_seen, last_sent, resolved_at FROM alert_state WHERE fingerprint = ?",
            (fingerprint,),
        ).fetchone()
        if row is None:
            return None
        return {
            "fingerprint": fingerprint,
            "severity": row[0],
            "first_seen": row[1],
            "last_sent": row[2],
            "resolved_at": row[3],
        }

    def upsert_alert_state(
        self,
        fingerprint: str,
        severity: str,
        first_seen: str,
        last_sent: str | None = None,
        resolved_at: str | None = None,
    ) -> None:
        """Insert or update alert state."""
        self._conn.execute(
            """INSERT OR REPLACE INTO alert_state
               (fingerprint, severity, first_seen, last_sent, resolved_at)
               VALUES (?, ?, ?, ?, ?)""",
            (fingerprint, severity, first_seen, last_sent, resolved_at),
        )
        self._conn.commit()

    def prune(self, days: int) -> int:
        """Delete runs older than *days*. Return count deleted."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cursor = self._conn.execute(
            "SELECT id FROM runs WHERE started_at < ?", (cutoff,)
        )
        run_ids = [r[0] for r in cursor.fetchall()]

        if not run_ids:
            return 0

        placeholders = ",".join("?" for _ in run_ids)
        self._conn.execute(
            f"DELETE FROM check_results WHERE run_id IN ({placeholders})", run_ids
        )
        self._conn.execute(
            f"DELETE FROM runs WHERE id IN ({placeholders})", run_ids
        )
        self._conn.commit()
        return len(run_ids)

    def close(self) -> None:
        self._conn.close()
