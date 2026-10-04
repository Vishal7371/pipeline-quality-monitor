"""Tests for the CLI."""

from pathlib import Path

from click.testing import CliRunner

from pqm.cli import main


PROJECT_ROOT = Path(__file__).parent.parent


def test_validate_config():
    runner = CliRunner()
    result = runner.invoke(main, ["validate-config", "--config", str(PROJECT_ROOT / "config" / "feeds.yaml")])
    assert result.exit_code == 0
    assert "valid" in result.output.lower()


def test_check_feed():
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-feed", "sales_csv",
        "--config", str(PROJECT_ROOT / "config" / "feeds.yaml"),
    ])
    assert result.exit_code == 0
    assert "sales_csv" in result.output
    assert "Rows:" in result.output


def test_check_feed_not_found():
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-feed", "nonexistent",
        "--config", str(PROJECT_ROOT / "config" / "feeds.yaml"),
    ])
    assert result.exit_code != 0


def test_init(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert Path("config/feeds.yaml").exists()
        assert Path("data/sales.csv").exists()
        assert Path("pqm.db").exists()


def test_run(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Init first
        runner.invoke(main, ["init"])
        # First run creates baseline
        result = runner.invoke(main, ["run", "--no-alerts"])
        assert result.exit_code == 0
        assert "baseline_created" in result.output.lower() or "BASELINE_CREATED" in result.output

        # Second run performs actual checks
        result = runner.invoke(main, ["run", "--no-alerts"])
        assert result.exit_code in (0, 1)  # pass or warn


def test_history(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(main, ["init"])
        runner.invoke(main, ["run", "--no-alerts"])

        result = runner.invoke(main, ["history"])
        assert result.exit_code == 0
        assert "sales_csv" in result.output
