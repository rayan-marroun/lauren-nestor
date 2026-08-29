"""Email-based approval gate.

Sends an email with Approve/Deny links pointing at the Cloud Run approval
service, then polls it until a decision is made or it times out. Times out
to "denied" -- silence is not consent.
"""
import os
import smtplib
import time
import uuid
from email.mime.text import MIMEText

import requests

POLL_SECONDS = 30
TIMEOUT_SECONDS = 24 * 3600


def _send_email(subject: str, body: str) -> None:
    address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    to = os.environ.get("APPROVAL_NOTIFY_TO", address)

    msg = MIMEText(body)
    msg["Subject"] = f"[Lauren Nestor] {subject}"
    msg["From"] = address
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(address, app_password)
        server.sendmail(address, [to], msg.as_string())


def notify_only(title: str, body: str) -> None:
    _send_email(title, body)


def request_approval(title: str, body: str) -> str:
    service_url = os.environ.get("APPROVAL_SERVICE_URL")
    action_id = str(uuid.uuid4())

    if not service_url:
        # No approval service deployed yet -- fail safe to denied, don't act.
        _send_email(
            f"NEEDS APPROVAL (service not deployed): {title}",
            f"{body}\n\nAPPROVAL_SERVICE_URL is not configured, so this "
            f"could not be auto-approved. Treating as denied.",
        )
        return "denied (no approval service configured)"

    requests.post(
        f"{service_url}/request",
        json={"id": action_id, "title": title, "body": body},
        timeout=15,
    )

    approve_link = f"{service_url}/approve/{action_id}"
    deny_link = f"{service_url}/deny/{action_id}"
    _send_email(
        f"Approval needed: {title}",
        f"{body}\n\nApprove: {approve_link}\nDeny: {deny_link}\n\n"
        f"No response within 24h is treated as denied.",
    )

    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            resp = requests.get(f"{service_url}/status/{action_id}", timeout=15)
            status = resp.json().get("status")
        except Exception:  # noqa: BLE001
            continue
        if status in ("approved", "denied"):
            return status
    return "denied (timeout)"
