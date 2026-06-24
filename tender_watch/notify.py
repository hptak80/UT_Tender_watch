"""
Versand von Benachrichtigungen per E-Mail (SMTP) und Telegram.

Alle Zugangsdaten kommen aus Umgebungsvariablen (siehe README.md), die im
GitHub-Actions-Workflow aus den Repo-"Secrets" befüllt werden. So landen
keine Passwörter/Tokens im Code.
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText

import requests

logger = logging.getLogger(__name__)


def _format_message(new_items: list[dict]) -> str:
    lines = [f"{len(new_items)} neue passende Ausschreibung(en) gefunden:\n"]
    for item in new_items:
        title = item.get("title_de") or item["title"]
        lines.append(f"• [{item['source']}] {title}")
        if item.get("keywords"):
            lines.append(f"  Stichworte: {', '.join(item['keywords'])}")
        if item.get("buyer"):
            lines.append(f"  Auftraggeber: {item['buyer']}")
        if item.get("country"):
            lines.append(f"  Land: {item['country']}")
        if item.get("published"):
            lines.append(f"  Veröffentlicht: {item['published']}")
        lines.append(f"  Link: {item['url']}")
        lines.append("")
    return "\n".join(lines)


def send_email(new_items: list[dict]) -> None:
    host = os.environ.get("SMTP_HOST")
    port = os.environ.get("SMTP_PORT")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    to_addr = os.environ.get("EMAIL_TO")

    if not all([host, port, user, password, to_addr]):
        logger.info("E-Mail-Versand übersprungen: nicht alle SMTP_* Secrets gesetzt.")
        return

    body = _format_message(new_items)
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = f"🔔 {len(new_items)} neue Ausschreibung(en): Ultraschallprüfsysteme"
    msg["From"] = user
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(host, int(port), timeout=30) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(user, [to_addr], msg.as_string())
        logger.info("E-Mail-Benachrichtigung versendet.")
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("E-Mail-Versand fehlgeschlagen: %s", exc)


def send_telegram(new_items: list[dict]) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.info("Telegram-Versand übersprungen: TELEGRAM_BOT_TOKEN/CHAT_ID nicht gesetzt.")
        return

    body = _format_message(new_items)
    # Telegram begrenzt Nachrichten auf 4096 Zeichen - bei vielen Treffern
    # in mehrere Nachrichten aufteilen statt abzuschneiden.
    chunks = [body[i : i + 3500] for i in range(0, len(body), 3500)] or [body]

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in chunks:
        try:
            resp = requests.post(
                url,
                json={"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True},
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Telegram-Versand fehlgeschlagen: %s", exc)
            break
    else:
        logger.info("Telegram-Benachrichtigung versendet.")


def notify(new_items: list[dict]) -> None:
    if not new_items:
        return
    send_email(new_items)
    send_telegram(new_items)
