"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pqm.profile import Profile, build_profile
from pqm.storage import Storage


DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def clean_df() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "clean.csv")


@pytest.fixture
def clean_profile(clean_df: pd.DataFrame) -> Profile:
    return build_profile(clean_df)


@pytest.fixture
def tmp_db(tmp_path: Path) -> str:
    return str(tmp_path / "test.db")


@pytest.fixture
def storage(tmp_db: str) -> Storage:
    s = Storage(tmp_db)
    yield s
    s.close()
