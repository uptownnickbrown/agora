"""Outbound email: transport + audit log + a tiny markdown-to-HTML renderer.

Providers (settings.email_provider):
- "console" (default/dev): logs the message and stores the full body in
  email_log so it can be inspected; nothing leaves the machine.
- "resend": one JSON POST to the Resend API via httpx — no SMTP, works on
  Railway. Attachments are base64-encoded inline.
"""
from __future__ import annotations

import base64
import html as html_mod
import logging
import re
import uuid
from dataclasses import dataclass, field

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import EmailLog

log = logging.getLogger("agora.email")

RESEND_URL = "https://api.resend.com/emails"


class EmailError(Exception):
    pass


@dataclass
class EmailMessage:
    to: str
    subject: str
    text: str  # plain-text part; markdown reads fine as text
    html: str | None = None
    # (filename, mime_type, content_str)
    attachments: list[tuple[str, str, str]] = field(default_factory=list)


async def deliver(msg: EmailMessage) -> str:
    """Transport only. Returns the provider message id ('' for console).
    Raises EmailError on delivery failure."""
    settings = get_settings()
    if settings.email_provider == "resend":
        return await _deliver_resend(msg, settings.resend_api_key, settings.email_from)
    log.info("email (console) to=%s subject=%r\n%s", msg.to, msg.subject, msg.text)
    return ""


async def _deliver_resend(msg: EmailMessage, api_key: str, sender: str) -> str:
    if not api_key:
        raise EmailError("email_provider=resend but AGORA_RESEND_API_KEY is unset")
    payload: dict = {"from": sender, "to": [msg.to], "subject": msg.subject,
                     "text": msg.text}
    if msg.html:
        payload["html"] = msg.html
    if msg.attachments:
        payload["attachments"] = [
            {"filename": name,
             "content": base64.b64encode(content.encode()).decode()}
            for name, _mime, content in msg.attachments
        ]
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            RESEND_URL, json=payload,
            headers={"Authorization": f"Bearer {api_key}"})
    if resp.status_code >= 300:
        raise EmailError(f"resend returned {resp.status_code}: {resp.text[:300]}")
    return resp.json().get("id", "")


async def send_logged(db: AsyncSession, msg: EmailMessage, *, kind: str,
                      world_id: uuid.UUID | None = None, ref: str = "") -> EmailLog:
    """deliver() + persist an EmailLog row. Console mode stores the full body
    so dev can read what would have been sent."""
    settings = get_settings()
    console = settings.email_provider == "console"
    try:
        provider_id = await deliver(msg)
        status = "console" if console else "sent"
    except EmailError as e:
        log.warning("email delivery failed to=%s kind=%s: %s", msg.to, kind, e)
        provider_id, status = "", "failed"
    row = EmailLog(world_id=world_id, to_email=msg.to, kind=kind, ref=ref,
                   subject=msg.subject[:255], status=status,
                   provider_id=provider_id,
                   body_text=msg.text if console else "")
    db.add(row)
    await db.flush()
    if status == "failed":
        raise EmailError(f"delivery to {msg.to} failed")
    return row


# -- markdown -> simple inline-styled HTML ------------------------------------

def _inline(s: str) -> str:
    s = html_mod.escape(s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", s)
    return s


def markdown_to_html(md: str) -> str:
    """Small renderer for our own playbook/digest markdown: #/##/### headings,
    -/1. lists, bold/italic, paragraphs. Mirrors the frontend's tiny renderer."""
    blocks: list[str] = []
    list_items: list[str] = []

    def flush() -> None:
        nonlocal list_items
        if list_items:
            blocks.append("<ul style='margin:4px 0 12px;padding-left:22px'>"
                          + "".join(list_items) + "</ul>")
            list_items = []

    for line in md.split("\n"):
        t = line.strip()
        if re.match(r"^#{1,2} ", t):
            flush()
            heading = re.sub(r"^#+ ", "", t)
            blocks.append(f"<h2 style='margin:18px 0 6px;font-size:18px'>"
                          f"{_inline(heading)}</h2>")
        elif t.startswith("### "):
            flush()
            blocks.append(f"<h3 style='margin:14px 0 4px;font-size:15px'>"
                          f"{_inline(t[4:])}</h3>")
        elif re.match(r"^[-*] ", t):
            list_items.append(f"<li>{_inline(t[2:])}</li>")
        elif re.match(r"^\d+\. ", t):
            item = re.sub(r"^\d+\. ", "", t)
            list_items.append(f"<li>{_inline(item)}</li>")
        elif t == "":
            flush()
        else:
            flush()
            blocks.append(f"<p style='margin:6px 0'>{_inline(t)}</p>")
    flush()
    return ("<div style=\"font-family:Georgia,'Times New Roman',serif;"
            "max-width:640px;margin:0 auto;color:#2b2b25;font-size:15px;"
            "line-height:1.55\">" + "".join(blocks) + "</div>")
