"""Profiler — compute summary statistics for a batch."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


# ---------------------------------------------------------------------------
# Type normalisation
# ---------------------------------------------------------------------------

TYPE_MAP: dict[str, str] = {
    "int64": "int",
    "int32": "int",
    "int16": "int",
    "int8": "int",
    "Int64": "int",
    "Int32": "int",
    "Int16": "int",
    "Int8": "int",
    "uint64": "int",
    "uint32": "int",
    "float64": "float",
    "float32": "float",
    "Float64": "float",
    "Float32": "float",
    "object": "string",
    "string": "string",
    "bool": "bool",
    "boolean": "bool",
    "datetime64[ns]": "datetime",
    "datetime64[ns, UTC]": "datetime",
    "category": "string",
}


def normalise_type(dtype: str) -> str:
    """Convert a pandas dtype string to one of: int, float, string, bool, datetime."""
    dtype_str = str(dtype)
    if dtype_str in TYPE_MAP:
        return TYPE_MAP[dtype_str]
    if "datetime" in dtype_str:
        return "datetime"
    if "int" in dtype_str.lower():
        return "int"
    if "float" in dtype_str.lower():
        return "float"
    return "string"


# ---------------------------------------------------------------------------
# Profile dataclass
# ---------------------------------------------------------------------------

@dataclass
class Profile:
    """Summary of a single batch: schema, null rates, ranges, row count."""

    schema: dict[str, str]
    row_count: int
    null_rates: dict[str, float]
    min_values: dict[str, float]
    max_values: dict[str, float]
    distinct_counts: dict[str, int]

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict (for baseline storage)."""
        return {
            "schema": self.schema,
            "row_count": self.row_count,
            "null_rates": self.null_rates,
            "min_values": self.min_values,
            "max_values": self.max_values,
            "distinct_counts": self.distinct_counts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Profile:
        """Deserialise from a dict (loaded from baseline JSON)."""
        return cls(
            schema=data["schema"],
            row_count=data["row_count"],
            null_rates=data["null_rates"],
            min_values=data.get("min_values", {}),
            max_values=data.get("max_values", {}),
            distinct_counts=data.get("distinct_counts", {}),
        )


# ---------------------------------------------------------------------------
# Build profile
# ---------------------------------------------------------------------------

def build_profile(df: pd.DataFrame) -> Profile:
    """Compute a Profile from a pandas DataFrame."""
    schema: dict[str, str] = {}
    null_rates: dict[str, float] = {}
    min_values: dict[str, float] = {}
    max_values: dict[str, float] = {}
    distinct_counts: dict[str, int] = {}

    row_count = len(df)

    for col in df.columns:
        col_str = str(col)
        dtype_str = str(df[col].dtype)
        schema[col_str] = normalise_type(dtype_str)

        if row_count > 0:
            null_rates[col_str] = float(df[col].isna().mean())
            distinct_counts[col_str] = int(df[col].nunique())

            if pd.api.types.is_numeric_dtype(df[col]):
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    min_values[col_str] = float(non_null.min())
                    max_values[col_str] = float(non_null.max())
        else:
            null_rates[col_str] = 0.0
            distinct_counts[col_str] = 0

    return Profile(
        schema=schema,
        row_count=row_count,
        null_rates=null_rates,
        min_values=min_values,
        max_values=max_values,
        distinct_counts=distinct_counts,
    )
