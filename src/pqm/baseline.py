"""Baseline store — save and load the last known-good profile per feed."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from pqm.profile import Profile


class BaselineStore:
    """Manages baselines in the SQLite `baselines` table."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS baselines (
                feed       TEXT PRIMARY KEY,
                profile    TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def load(self, feed: str) -> Profile | None:
        """Return the stored baseline Profile for *feed*, or None."""
        row = self._conn.execute(
            "SELECT profile FROM baselines WHERE feed = ?", (feed,)
        ).fetchone()
        if row is None:
            return None
        data = json.loads(row[0])
        return Profile.from_dict(data)

    def save(self, feed: str, profile: Profile) -> None:
        """Insert or replace the baseline for *feed*."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT OR REPLACE INTO baselines (feed, profile, updated_at) VALUES (?, ?, ?)",
            (feed, json.dumps(profile.to_dict()), now),
        )
        self._conn.commit()

    def exists(self, feed: str) -> bool:
        """Check whether a baseline exists for *feed*."""
        row = self._conn.execute(
            "SELECT 1 FROM baselines WHERE feed = ?", (feed,)
        ).fetchone()
        return row is not None

    def close(self) -> None:
        self._conn.close()
