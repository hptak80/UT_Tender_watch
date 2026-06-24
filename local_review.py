"""
Lokale Nachbearbeitung der Ausschreibungs-Warteschlange mit Ollama/Qwen.

Läuft auf DEINEM PC (nicht in GitHub Actions). Holt die Treffer, die der
Cloud-Lauf in state/pending_review.json abgelegt hat, lässt sie durch dein
lokales Modell (über Ollama, z.B. Qwen via Hermes) übersetzen/bewerten/mit
Stichworten versehen, schickt eine "veredelte" Benachrichtigung für die
tatsächlich relevanten Treffer und leert die Warteschlange danach wieder.

Voraussetzungen:
- Python 3 + `pip install requests` (einmalig)
- Ollama läuft lokal, gewünschtes Modell ist gezogen
- local_secrets.py existiert und ist ausgefüllt (siehe local_secrets.py.example)

Aufruf: python local_review.py
(am besten regelmäßig per Windows-Aufgabenplanung, solange dein PC läuft -
siehe README.md)
"""
from __future__ import annotations

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

try:
    import local_secrets as secrets
except ImportError:
    logger.error(
        "local_secrets.py fehlt. Kopiere local_secrets.py.example zu "
        "local_secrets.py und trag deine Werte ein."
    )
    sys.exit(1)

# Zugangsdaten für notify.py als Umgebungsvariablen setzen, damit das
# bestehende tender_watch.notify-Modul unverändert wiederverwendet werden kann.
for var in (
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASS",
    "EMAIL_TO",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
):
    value = getattr(secrets, var, "")
    if value:
        os.environ[var] = value

from tender_watch.github_queue import fetch_pending, write_pending  # noqa: E402
from tender_watch.notify import notify  # noqa: E402
from tender_watch.ollama_review import review_items  # noqa: E402


def main() -> int:
    logger.info("Hole Warteschlange von GitHub...")
    try:
        items, sha = fetch_pending(
            secrets.GITHUB_OWNER,
            secrets.GITHUB_REPO,
            secrets.GITHUB_TOKEN,
            getattr(secrets, "GITHUB_BRANCH", "main"),
        )
    except Exception:
        logger.exception(
            "Konnte Warteschlange nicht laden. GITHUB_TOKEN/OWNER/REPO in "
            "local_secrets.py korrekt?"
        )
        return 1

    logger.info("%d Treffer in der Warteschlange.", len(items))
    if not items:
        logger.info("Nichts zu tun.")
        return 0

    reviewed = review_items(items, secrets.OLLAMA_URL, secrets.OLLAMA_MODEL)
    logger.info(
        "Ollama-Bewertung abgeschlossen: %d von %d Treffern als relevant eingestuft.",
        len(reviewed),
        len(items),
    )

    if reviewed:
        notify(reviewed)
        for item in reviewed:
            logger.info(
                "VEREDELT: [%s] %s -> %s",
                item["source"],
                item.get("title_de", item["title"]),
                item["url"],
            )

    logger.info("Leere Warteschlange auf GitHub...")
    try:
        write_pending(
            secrets.GITHUB_OWNER,
            secrets.GITHUB_REPO,
            secrets.GITHUB_TOKEN,
            [],  # alle verarbeiteten Treffer raus
            sha,
            getattr(secrets, "GITHUB_BRANCH", "main"),
        )
    except Exception:
        logger.exception(
            "Konnte Warteschlange nicht leeren - beim nächsten Lauf werden "
            "dieselben Treffer ggf. erneut verarbeitet (nicht schlimm, nur "
            "etwas Mehrarbeit)."
        )
        return 1

    logger.info("Fertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
