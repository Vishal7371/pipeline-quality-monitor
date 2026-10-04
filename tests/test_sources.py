"""Tests for data sources."""

from pathlib import Path

import pandas as pd
import pytest

from pqm.sources.csv_source import CsvSource


DATA_DIR = Path(__file__).parent / "data"


class TestCsvSource:
    def test_read_batch(self):
        src = CsvSource(str(DATA_DIR / "clean.csv"))
        df = src.read_batch()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5

    def test_describe(self):
        src = CsvSource(str(DATA_DIR / "clean.csv"))
        schema = src.describe()
        assert "order_id" in schema
        assert schema["order_id"] == "int"
        assert schema["email"] == "string"

    def test_last_modified_time(self):
        src = CsvSource(str(DATA_DIR / "clean.csv"))
        mtime = src.last_modified_time()
        assert mtime is not None
        assert isinstance(mtime, float)

    def test_missing_file(self):
        src = CsvSource("/nonexistent/file.csv")
        with pytest.raises(FileNotFoundError):
            src.read_batch()

    def test_empty_file(self):
        src = CsvSource(str(DATA_DIR / "empty.csv"))
        df = src.read_batch()
        assert len(df) == 0
        assert len(df.columns) == 5

    def test_contract_schema_shape(self):
        """Contract test: all sources return the same shape for equivalent data."""
        src = CsvSource(str(DATA_DIR / "clean.csv"))
        schema = src.describe()
        # Must be dict[str, str] with canonical type values
        for col, dtype in schema.items():
            assert isinstance(col, str)
            assert dtype in ("int", "float", "string", "bool", "datetime")
