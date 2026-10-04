"""Source protocol and factory."""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class Source(Protocol):
    """Interface every data source must implement."""

    def read_batch(self) -> pd.DataFrame: ...
    def describe(self) -> dict[str, str]: ...
    def last_modified_time(self) -> float | None: ...


def create_source(feed_type: str, **kwargs: object) -> Source:
    """Factory: return the right Source subclass based on feed type."""
    if feed_type == "csv":
        from pqm.sources.csv_source import CsvSource
        return CsvSource(location=str(kwargs["location"]))
    elif feed_type == "sql":
        from pqm.sources.sql_source import SqlSource
        return SqlSource(
            location=str(kwargs["location"]),
            table=str(kwargs.get("table", "")) or None,
            query=str(kwargs.get("query", "")) or None,
        )
    else:
        raise ValueError(f"Unknown source type: {feed_type}")
