"""Slack alert channel."""

from __future__ import annotations

import json
import logging

import requests

from pqm.config import SlackConfig
from pqm.storage import CheckResult

logger = logging.getLogger(__name__)


def format_slack_message(feed_name: str, result: CheckResult) -> dict:
    """Format a CheckResult into a Slack message payload."""
    status_emoji = {"pass": "✅", "warn": "⚠️", "fail": "🚨"}.get(result.status, "❓")
    status_label = result.status.upper()

    text = f"{status_emoji} [{status_label}] {feed_name}: {result.check}\n{result.message}"

    # Add key details as a compact block
    detail_lines = []
    for k, v in result.details.items():
        if k not in ("column", "resolved"):
            detail_lines.append(f"• {k}: {v}")

    if detail_lines:
        text += "\n" + "\n".join(detail_lines[:5])

    text += f"\nRun: `pqm history --feed {feed_name}`"

    return {
        "text": text,
        "unfurl_links": False,
    }


def send_slack_alert(
    feed_name: str,
    result: CheckResult,
    config: SlackConfig,
) -> None:
    """Send an alert to Slack via incoming webhook."""
    webhook_url = config.get_webhook_url()
    if not webhook_url:
        logger.warning(
            "Slack webhook not configured (set %s env var)", config.webhook_env
        )
        return

    payload = format_slack_message(feed_name, result)

    resp = requests.post(
        webhook_url,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )

    if resp.status_code != 200:
        logger.error("Slack API error %s: %s", resp.status_code, resp.text)
        raise RuntimeError(f"Slack webhook returned {resp.status_code}")

    logger.debug("Slack alert sent for %s/%s", feed_name, result.check)
