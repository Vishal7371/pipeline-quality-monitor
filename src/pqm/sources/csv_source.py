"""CSV data source."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pqm.profile import normalise_type


class CsvSource:
    """Read a CSV file as a data batch."""

    def __init__(self, location: str) -> None:
        self.path = Path(location)

    def read_batch(self) -> pd.DataFrame:
        """Read the entire CSV file into a DataFrame."""
        if not self.path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.path}")
        return pd.read_csv(self.path)

    def describe(self) -> dict[str, str]:
        """Return {column: normalised_type} from a small sample."""
        if not self.path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.path}")
        sample = pd.read_csv(self.path, nrows=5)
        return {str(col): normalise_type(str(sample[col].dtype)) for col in sample.columns}

    def last_modified_time(self) -> float | None:
        """Return file mtime as a unix timestamp."""
        if not self.path.exists():
            return None
        return self.path.stat().st_mtime
