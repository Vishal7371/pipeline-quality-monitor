"""CLI entry points for PQM."""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import click

from pqm.config import load_config, PQMConfig, FeedConfig
from pqm.sources import create_source
from pqm.profile import build_profile
from pqm.baseline import BaselineStore
from pqm.storage import Storage, Run, CheckResult
from pqm.checks import run_checks
from pqm.alerts import process_alerts


def _setup_logging() -> None:
    import os
    level = os.environ.get("PQM_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _status_symbol(status: str) -> str:
    return {"pass": "✅", "warn": "⚠️ ", "fail": "🚨", "error": "💥", "baseline_created": "📋"}.get(
        status, "?"
    )


# ---------------------------------------------------------------------------
# Core run logic (shared by `run` and `check-feed`)
# ---------------------------------------------------------------------------

def _run_feed(
    feed: FeedConfig,
    config: PQMConfig,
    storage: Storage,
    baseline_store: BaselineStore,
    send_alerts: bool = True,
) -> Run:
    """Execute checks for one feed. Returns the Run object."""
    logger = logging.getLogger("pqm")
    started = datetime.now(timezone.utc)

    try:
        # 1. Read batch
        source = create_source(feed.type, location=feed.location, table=feed.table, query=feed.query)
        df = source.read_batch()
        source_mtime = source.last_modified_time()

        # 2. Build profile
        profile = build_profile(df)

        # 3. Load or create baseline
        baseline = baseline_store.load(feed.name)
        if baseline is None:
            baseline_store.save(feed.name, profile)
            run = Run(
                id=None,
                feed=feed.name,
                started_at=started,
                finished_at=datetime.now(timezone.utc),
                row_count=profile.row_count,
                status="baseline_created",
                results=[],
            )
            storage.save_run(run)
            logger.info("Baseline created for '%s' (%d rows, %d columns)",
                        feed.name, profile.row_count, len(profile.schema))
            return run

        # 4. Run checks
        results = run_checks(feed, df, profile, baseline, storage, source_mtime)

        # 5. Determine overall status
        statuses = [r.status for r in results]
        if "fail" in statuses:
            overall = "fail"
        elif "warn" in statuses:
            overall = "warn"
        else:
            overall = "pass"

        finished = datetime.now(timezone.utc)
        run = Run(
            id=None,
            feed=feed.name,
            started_at=started,
            finished_at=finished,
            row_count=profile.row_count,
            status=overall,
            results=results,
        )

        # 6. Save run
        storage.save_run(run)

        # 7. Send alerts
        if send_alerts:
            process_alerts(
                feed, results, config.alerts, storage,
                config.settings.alert_cooldown_minutes,
            )

        # 8. Update baseline only if passed
        if overall == "pass":
            baseline_store.save(feed.name, profile)
            logger.debug("Baseline updated for '%s'", feed.name)

        return run

    except Exception as e:
        finished = datetime.now(timezone.utc)
        run = Run(
            id=None,
            feed=feed.name,
            started_at=started,
            finished_at=finished,
            row_count=None,
            status="error",
            results=[CheckResult(
                check="runtime",
                status="fail",
                message=str(e),
                details={"error_type": type(e).__name__},
            )],
        )
        storage.save_run(run)
        logger.error("Error running feed '%s': %s", feed.name, e)
        return run


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

@click.group()
def main() -> None:
    """Pipeline Quality Monitor — watch your data feeds."""
    _setup_logging()


@main.command()
def init() -> None:
    """Create sample config and database."""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    config_path = config_dir / "feeds.yaml"
    if config_path.exists():
        click.echo(f"Config already exists: {config_path}")
    else:
        sample = """\
settings:
  database: pqm.db
  alert_cooldown_minutes: 60
  default_severity:
    schema_drift: fail
    null_rate: warn

alerts:
  slack:
    webhook_env: PQM_SLACK_WEBHOOK

feeds:
  - name: sales_csv
    type: csv
    location: data/sales.csv
    freshness_max_age_minutes: 90
    checks:
      schema_drift: true
      null_rate:
        columns:
          customer_id: 0.0
          email: 0.05
      duplicates:
        key: [order_id]
      range:
        amount: {min: 0, max: 100000}
      row_count:
        tolerance_pct: 40
"""
        config_path.write_text(sample)
        click.echo(f"✅ Created {config_path}")

    # Create sample CSV
    csv_path = data_dir / "sales.csv"
    if not csv_path.exists():
        csv_path.write_text(
            "order_id,customer_id,email,amount,created_at\n"
            "1,C001,alice@example.com,250.00,2026-09-30 10:00:00\n"
            "2,C002,bob@example.com,125.50,2026-09-30 11:00:00\n"
            "3,C003,carol@example.com,899.99,2026-09-30 12:00:00\n"
            "4,C004,dave@example.com,45.00,2026-09-30 13:00:00\n"
            "5,C005,eve@example.com,1200.00,2026-09-30 14:00:00\n"
        )
        click.echo(f"✅ Created {csv_path}")

    # Initialise database
    config = load_config(config_path)
    Storage(config.settings.database)
    click.echo(f"✅ Database ready: {config.settings.database}")


@main.command("validate-config")
@click.option("--config", "config_path", default=None, help="Path to config file")
def validate_config(config_path: str | None) -> None:
    """Validate feeds.yaml and exit."""
    try:
        config = load_config(config_path)
        click.echo(f"✅ Config is valid: {len(config.feeds)} feed(s) defined")
        for f in config.feeds:
            checks = [k for k, v in f.checks.items() if v]
            click.echo(f"   • {f.name} ({f.type}) — checks: {', '.join(checks) or 'defaults'}")
    except Exception as e:
        click.echo(f"❌ Config error: {e}", err=True)
        sys.exit(3)


@main.command("check-feed")
@click.argument("name")
@click.option("--config", "config_path", default=None)
def check_feed(name: str, config_path: str | None) -> None:
    """Read one feed, print schema and row count. No alerts."""
    config = load_config(config_path)
    feed = next((f for f in config.feeds if f.name == name), None)
    if feed is None:
        click.echo(f"❌ Feed '{name}' not found in config", err=True)
        sys.exit(3)

    source = create_source(feed.type, location=feed.location, table=feed.table, query=feed.query)
    df = source.read_batch()
    profile = build_profile(df)

    click.echo(f"\n📊 Feed: {name}")
    click.echo(f"   Rows: {profile.row_count}")
    click.echo(f"   Columns ({len(profile.schema)}):")
    for col, dtype in profile.schema.items():
        null_pct = profile.null_rates.get(col, 0) * 100
        click.echo(f"     {col:<30s} {dtype:<10s} nulls: {null_pct:.1f}%")


@main.command()
@click.option("--feed", "feed_name", default=None, help="Run a single feed")
@click.option("--no-alerts", is_flag=True, help="Suppress alerts")
@click.option("--config", "config_path", default=None)
def run(feed_name: str | None, no_alerts: bool, config_path: str | None) -> None:
    """Full run: checks, storage, alerts."""
    config = load_config(config_path)
    storage = Storage(config.settings.database)
    baseline_store = BaselineStore(config.settings.database)

    feeds = config.feeds
    if feed_name:
        feeds = [f for f in feeds if f.name == feed_name]
        if not feeds:
            click.echo(f"❌ Feed '{feed_name}' not found", err=True)
            sys.exit(3)

    worst = "pass"
    for feed in feeds:
        click.echo(f"\n{'─' * 50}")
        click.echo(f"Running: {feed.name}")

        result = _run_feed(feed, config, storage, baseline_store, send_alerts=not no_alerts)

        sym = _status_symbol(result.status)
        click.echo(f"{sym} {feed.name}: {result.status.upper()}", nl=False)
        if result.row_count is not None:
            click.echo(f" ({result.row_count} rows)")
        else:
            click.echo()

        for cr in result.results:
            s = _status_symbol(cr.status)
            click.echo(f"   {s} {cr.check}: {cr.message}")

        # Track worst status
        if result.status == "fail" or result.status == "error":
            worst = "fail"
        elif result.status == "warn" and worst == "pass":
            worst = "warn"

    baseline_store.close()
    storage.close()

    click.echo(f"\n{'═' * 50}")
    click.echo(f"Overall: {_status_symbol(worst)} {worst.upper()}")

    # Exit codes per spec
    if worst == "fail":
        sys.exit(2)
    elif worst == "warn":
        sys.exit(1)
    sys.exit(0)


@main.command()
@click.option("--feed", "feed_name", default=None)
@click.option("--limit", default=20, type=int)
@click.option("--config", "config_path", default=None)
def history(feed_name: str | None, limit: int, config_path: str | None) -> None:
    """Show recent runs and failures."""
    config = load_config(config_path)
    storage = Storage(config.settings.database)

    runs = storage.get_recent_runs(feed_name, limit)

    if not runs:
        click.echo("No runs found.")
        storage.close()
        return

    click.echo(f"\n{'Run ID':<8} {'Feed':<20} {'Status':<10} {'Rows':<10} {'Started At'}")
    click.echo("─" * 80)
    for r in runs:
        sym = _status_symbol(r.status)
        rows = str(r.row_count) if r.row_count is not None else "—"
        click.echo(
            f"{r.id or 0:<8} {r.feed:<20} {sym}{r.status:<7} {rows:<10} "
            f"{r.started_at.strftime('%Y-%m-%d %H:%M')}"
        )

        # Show failures inline
        failures = [cr for cr in r.results if cr.status != "pass"]
        for cr in failures:
            click.echo(f"         └─ {_status_symbol(cr.status)} {cr.check}: {cr.message}")

    storage.close()


@main.command("accept-schema")
@click.argument("feed_name")
@click.option("--config", "config_path", default=None)
def accept_schema(feed_name: str, config_path: str | None) -> None:
    """Replace the baseline with the current schema for a feed."""
    config = load_config(config_path)
    feed = next((f for f in config.feeds if f.name == feed_name), None)
    if feed is None:
        click.echo(f"❌ Feed '{feed_name}' not found", err=True)
        sys.exit(3)

    source = create_source(feed.type, location=feed.location, table=feed.table, query=feed.query)
    df = source.read_batch()
    profile = build_profile(df)

    baseline_store = BaselineStore(config.settings.database)
    old = baseline_store.load(feed_name)

    baseline_store.save(feed_name, profile)
    baseline_store.close()

    click.echo(f"✅ Baseline updated for '{feed_name}'")
    if old:
        old_cols = set(old.schema.keys())
        new_cols = set(profile.schema.keys())
        added = new_cols - old_cols
        removed = old_cols - new_cols
        if added:
            click.echo(f"   Added columns: {', '.join(sorted(added))}")
        if removed:
            click.echo(f"   Removed columns: {', '.join(sorted(removed))}")

        changed = [c for c in old_cols & new_cols if old.schema[c] != profile.schema[c]]
        if changed:
            for c in changed:
                click.echo(f"   Type changed: {c} ({old.schema[c]} → {profile.schema[c]})")


@main.command()
@click.option("--config", "config_path", default=None)
def schedule(config_path: str | None) -> None:
    """Run feeds on their cron schedules (long-running)."""
    from croniter import croniter

    config = load_config(config_path)
    storage = Storage(config.settings.database)
    baseline_store = BaselineStore(config.settings.database)

    scheduled_feeds = [f for f in config.feeds if f.schedule]
    if not scheduled_feeds:
        click.echo("No feeds have schedules configured.")
        return

    click.echo(f"Scheduler started for {len(scheduled_feeds)} feed(s). Press Ctrl+C to stop.")
    for f in scheduled_feeds:
        click.echo(f"  • {f.name}: {f.schedule}")

    # Build next-run times
    now = datetime.now()
    crons = {f.name: croniter(f.schedule, now) for f in scheduled_feeds}
    next_runs = {f.name: crons[f.name].get_next(datetime) for f in scheduled_feeds}

    try:
        while True:
            now = datetime.now()
            for feed in scheduled_feeds:
                if now >= next_runs[feed.name]:
                    click.echo(f"\n⏰ Running scheduled: {feed.name}")
                    _run_feed(feed, config, storage, baseline_store, send_alerts=True)
                    next_runs[feed.name] = crons[feed.name].get_next(datetime)

            time.sleep(30)  # Check every 30 seconds
    except KeyboardInterrupt:
        click.echo("\nScheduler stopped.")
    finally:
        baseline_store.close()
        storage.close()


@main.command()
@click.option("--days", required=True, type=int, help="Delete runs older than N days")
@click.option("--config", "config_path", default=None)
def prune(days: int, config_path: str | None) -> None:
    """Delete history older than N days."""
    config = load_config(config_path)
    storage = Storage(config.settings.database)

    deleted = storage.prune(days)
    storage.close()

    click.echo(f"🗑️  Deleted {deleted} run(s) older than {days} days.")


if __name__ == "__main__":
    main()
