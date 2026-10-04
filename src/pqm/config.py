"""Configuration loader — parse and validate feeds.yaml with Pydantic."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Settings models
# ---------------------------------------------------------------------------

class DefaultSeverity(BaseModel):
    schema_drift: str = "fail"
    null_rate: str = "warn"


class SlackConfig(BaseModel):
    webhook_env: str = "PQM_SLACK_WEBHOOK"

    def get_webhook_url(self) -> Optional[str]:
        return os.environ.get(self.webhook_env)


class EmailConfig(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    username_env: str = "PQM_SMTP_USER"
    password_env: str = "PQM_SMTP_PASSWORD"
    from_addr: str = Field(alias="from")
    to: List[str]

    model_config = {"populate_by_name": True}

    def get_username(self) -> Optional[str]:
        return os.environ.get(self.username_env)

    def get_password(self) -> Optional[str]:
        return os.environ.get(self.password_env)


class AlertsConfig(BaseModel):
    slack: Optional[SlackConfig] = None
    email: Optional[EmailConfig] = None


class Settings(BaseModel):
    database: str = "pqm.db"
    alert_cooldown_minutes: int = 60
    default_severity: DefaultSeverity = DefaultSeverity()


# ---------------------------------------------------------------------------
# Check settings models
# ---------------------------------------------------------------------------

class NullRateSettings(BaseModel):
    columns: Dict[str, float]


class DuplicatesSettings(BaseModel):
    key: List[str]


class RangeEntry(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None


class RowCountSettings(BaseModel):
    tolerance_pct: float = 40.0
    window_runs: int = 10


# ---------------------------------------------------------------------------
# Feed model
# ---------------------------------------------------------------------------

class FeedConfig(BaseModel):
    name: str
    type: str
    location: str
    table: Optional[str] = None
    query: Optional[str] = None
    schedule: Optional[str] = None
    freshness_max_age_minutes: Optional[int] = None
    freshness_column: Optional[str] = None
    checks: Dict[str, Any] = {}

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("csv", "sql"):
            raise ValueError(f"Feed type must be 'csv' or 'sql', got '{v}'")
        return v

    @model_validator(mode="after")
    def sql_needs_table_or_query(self) -> "FeedConfig":
        if self.type == "sql" and not self.table and not self.query:
            raise ValueError("SQL feeds require either 'table' or 'query'")
        return self

    # ---- Convenience helpers to parse check sub-configs ----

    def get_null_rate_settings(self) -> Optional[NullRateSettings]:
        raw = self.checks.get("null_rate")
        if raw is None or raw is False:
            return None
        if isinstance(raw, dict):
            return NullRateSettings(**raw)
        return None

    def get_duplicates_settings(self) -> Optional[DuplicatesSettings]:
        raw = self.checks.get("duplicates")
        if raw is None or raw is False:
            return None
        if isinstance(raw, dict):
            return DuplicatesSettings(**raw)
        return None

    def get_range_settings(self) -> Optional[Dict[str, RangeEntry]]:
        raw = self.checks.get("range")
        if raw is None or raw is False:
            return None
        if isinstance(raw, dict):
            return {col: RangeEntry(**bounds) for col, bounds in raw.items()}
        return None

    def get_row_count_settings(self) -> RowCountSettings:
        raw = self.checks.get("row_count")
        if isinstance(raw, dict):
            return RowCountSettings(**raw)
        return RowCountSettings()

    def is_check_enabled(self, check_name: str) -> bool:
        val = self.checks.get(check_name)
        if val is None:
            return False
        if val is False:
            return False
        return True


# ---------------------------------------------------------------------------
# Root config
# ---------------------------------------------------------------------------

class PQMConfig(BaseModel):
    settings: Settings = Settings()
    alerts: AlertsConfig = AlertsConfig()
    feeds: List[FeedConfig]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = "config/feeds.yaml"


def load_config(path: Union[str, Path, None] = None) -> PQMConfig:
    """Load and validate the YAML config file.

    Resolution order:
      1. Explicit *path* argument
      2. PQM_CONFIG environment variable
      3. config/feeds.yaml (relative to cwd)
    """
    if path is None:
        path = os.environ.get("PQM_CONFIG", DEFAULT_CONFIG_PATH)

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError(f"Config file is empty: {config_path}")

    return PQMConfig(**raw)
