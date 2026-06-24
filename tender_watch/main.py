"""
Hauptskript des Ausschreibungs-Watchers (Cloud-Teil, läuft via GitHub Actions).

Ablauf bei jedem Lauf:
1. Alle aktivierten Quellen abfragen (TED, UK Find a Tender, ...).
2. Treffer mit bereits bekannten IDs (state/seen.json) abgleichen.
3. Regelbasierten Filter anwenden (kein KI, keine Tokenkosten - siehe
   tender_watch/rule_filter.py).
4. Optional (CLOUD_NOTIFY=True): sofortige Roh-Benachrichtigung senden.
5. Treffer in die Warteschlange für die lokale Ollama/Qwen-Nachbearbeitung
   legen (state/pending_review.json) - die übersetzt, vergibt Stichworte
   und prüft nochmal die Relevanz, sobald dein PC läuft (local_review.py).
6. state/seen.json + state/pending_review.json aktualisieren (Commit
   passiert im GitHub-Actions-Workflow).

Aufruf: python -m tender_watch.main
"""
from __future__ import annotations

import logging
import sys

from config import CLOUD_NOTIFY, ENABLE_TED, ENABLE_UK_FTS
from tender_watch.notify import notify
from tender_watch.queue_state import enqueue
from tender_watch.rule_filter import apply_rule_filter
from tender_watch.state import load_seen, save_seen

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def collect_all_notices() -> list[dict]:
    notices: list[dict] = []

    if ENABLE_TED:
        try:
            from tender_watch.ted_source import fetch_notices as fetch_ted

            ted_results = fetch_ted()
            logger.info("TED: %d Treffer im Suchfenster.", len(ted_results))
            notices.extend(ted_results)
        except Exception:  # noqa: BLE001 - eine Quelle darf den Lauf nicht killen
            logger.exception("Fehler bei der TED-Abfrage, Quelle wird übersprungen.")

    if ENABLE_UK_FTS:
        try:
            from tender_watch.uk_source import fetch_notices as fetch_uk

            uk_results = fetch_uk()
            logger.info("UK Find a Tender: %d Treffer im Suchfenster.", len(uk_results))
            notices.extend(uk_results)
        except Exception:  # noqa: BLE001
            logger.exception("Fehler bei der UK-FTS-Abfrage, Quelle wird übersprungen.")

    return notices


def main() -> int:
    seen = load_seen()
    all_notices = collect_all_notices()

    new_items = [n for n in all_notices if n["id"] not in seen]
    logger.info(
        "%d Treffer insgesamt, davon %d neu (vorher unbekannt).",
        len(all_notices),
        len(new_items),
    )

    candidates = apply_rule_filter(new_items)
    if len(candidates) != len(new_items):
        logger.info(
            "Regel-Filter: %d von %d neuen Treffern aussortiert.",
            len(new_items) - len(candidates),
            len(new_items),
        )

    if candidates:
        if CLOUD_NOTIFY:
            notify(candidates)
        enqueue(candidates)
        for item in candidates:
            logger.info(
                "NEU (Cloud, ungefiltert/unübersetzt): [%s] %s -> %s",
                item["source"],
                item["title"],
                item["url"],
            )
        logger.info(
            "%d Treffer in die Warteschlange für die lokale Ollama-Nachbearbeitung gelegt.",
            len(candidates),
        )

    seen.update(n["id"] for n in all_notices)
    save_seen(seen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
