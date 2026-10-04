"""Email alert channel."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pqm.config import EmailConfig
from pqm.storage import CheckResult

logger = logging.getLogger(__name__)


def format_email(feed_name: str, result: CheckResult) -> tuple[str, str, str]:
    """Format a CheckResult into email subject, plain text, and HTML body."""
    status_label = result.status.upper()
    subject = f"[PQM {status_label}] {feed_name}: {result.check}"

    # Plain text
    plain = f"Feed: {feed_name}\nCheck: {result.check}\nStatus: {status_label}\n\n"
    plain += f"{result.message}\n\n"
    plain += "Details:\n"
    for k, v in result.details.items():
        plain += f"  {k}: {v}\n"
    plain += f"\nRun: pqm history --feed {feed_name}\n"

    # HTML
    status_color = {"pass": "#22c55e", "warn": "#f59e0b", "fail": "#ef4444"}.get(
        result.status, "#6b7280"
    )
    html = f"""<html><body>
    <h2 style="color: {status_color}">[{status_label}] {feed_name}: {result.check}</h2>
    <p>{result.message}</p>
    <table border="1" cellpadding="4" cellspacing="0" style="border-collapse: collapse;">
      <tr><th>Key</th><th>Value</th></tr>
    """
    for k, v in result.details.items():
        html += f"  <tr><td>{k}</td><td>{v}</td></tr>\n"
    html += f"""</table>
    <p><code>pqm history --feed {feed_name}</code></p>
    </body></html>"""

    return subject, plain, html


def send_email_alert(
    feed_name: str,
    result: CheckResult,
    config: EmailConfig,
) -> None:
    """Send an alert email via SMTP."""
    username = config.get_username()
    password = config.get_password()

    if not username or not password:
        logger.warning(
            "Email credentials not configured (set %s and %s env vars)",
            config.username_env,
            config.password_env,
        )
        return

    subject, plain, html = format_email(feed_name, result)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.from_addr
    msg["To"] = ", ".join(config.to)

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(config.from_addr, config.to, msg.as_string())
        logger.debug("Email alert sent for %s/%s", feed_name, result.check)
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        raise
