"""SQL data source (via SQLAlchemy)."""

from __future__ import annotations

import sqlalchemy as sa
import pandas as pd

from pqm.profile import normalise_type


# Map SQLAlchemy generic types to our canonical types
_SA_TYPE_MAP: dict[str, str] = {
    "INTEGER": "int",
    "BIGINT": "int",
    "SMALLINT": "int",
    "FLOAT": "float",
    "REAL": "float",
    "NUMERIC": "float",
    "DECIMAL": "float",
    "VARCHAR": "string",
    "TEXT": "string",
    "CHAR": "string",
    "NVARCHAR": "string",
    "BOOLEAN": "bool",
    "DATETIME": "datetime",
    "TIMESTAMP": "datetime",
    "DATE": "datetime",
}


def _sa_type_to_canonical(sa_type: object) -> str:
    """Convert a SQLAlchemy column type to a canonical type string."""
    type_name = type(sa_type).__name__.upper()
    return _SA_TYPE_MAP.get(type_name, "string")


class SqlSource:
    """Read a SQL table or query as a data batch."""

    def __init__(
        self,
        location: str,
        table: str | None = None,
        query: str | None = None,
    ) -> None:
        self.url = location
        self.table = table
        self.query = query
        self._engine = sa.create_engine(location)

    def _get_sql(self) -> str:
        if self.query:
            return self.query
        if self.table:
            return f"SELECT * FROM {self.table}"
        raise ValueError("SQL source needs either 'table' or 'query'")

    def read_batch(self) -> pd.DataFrame:
        """Execute the query and return the result as a DataFrame."""
        with self._engine.connect() as conn:
            return pd.read_sql(sa.text(self._get_sql()), conn)

    def describe(self) -> dict[str, str]:
        """Return {column: canonical_type} using SQLAlchemy inspection."""
        if self.table:
            inspector = sa.inspect(self._engine)
            columns = inspector.get_columns(self.table)
            return {col["name"]: _sa_type_to_canonical(col["type"]) for col in columns}
        else:
            # For raw queries, read a small sample and infer from pandas dtypes
            with self._engine.connect() as conn:
                sample = pd.read_sql(sa.text(self._get_sql()), conn).head(5)
            return {
                str(col): normalise_type(str(sample[col].dtype))
                for col in sample.columns
            }

    def last_modified_time(self) -> float | None:
        """SQL sources don't have a file mtime; return None.

        Freshness for SQL is handled via freshness_column in the check.
        """
        return None
