"""
Quelle: TED (Tenders Electronic Daily) - offizielles EU-Ausschreibungsportal.

Offizielle, unauthentifizierte Such-API: POST https://api.ted.europa.eu/v3/notices/search
Doku: https://docs.ted.europa.eu/api/latest/search.html
Swagger: https://api.ted.europa.eu/swagger-ui/index.html#/Search/search

WICHTIG: TED hat im Lauf der Zeit schon mehrfach Feldnamen/Endpunkte
geändert (eForms-Umstellung). Wenn dieses Modul plötzlich 0 Treffer liefert,
obwohl es vorher funktioniert hat, zuerst hier prüfen, ob sich an der
Query-Syntax etwas geändert hat:
https://ted.europa.eu/en/expert-search  (dort kannst du eine Suche bauen,
auf "Expert Mode" umschalten und die exakte Syntax abschauen).
"""
from __future__ import annotations

import datetime as dt
import logging

import requests

from config import CPV_CODES, KEYWORDS, LOOKBACK_DAYS

logger = logging.getLogger(__name__)

TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"

FIELDS = [
    "publication-number",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "publication-date",
    "deadline-receipt-request",
]


def _build_query() -> str:
    since = (dt.date.today() - dt.timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")

    keyword_clauses = [f'FT="{kw}"' for kw in KEYWORDS]
    cpv_clauses = [f"classification-cpv={code}" for code in CPV_CODES]

    or_block = " OR ".join(keyword_clauses + cpv_clauses)
    return f"(({or_block}) AND PD>={since})"


def fetch_notices() -> list[dict]:
    """Holt aktuelle TED-Treffer und gibt sie als Liste normalisierter dicts zurück."""
    query = _build_query()
    payload = {
        "query": query,
        "fields": FIELDS,
        "limit": 250,
        "scope": "ACTIVE",
        "checkQuerySyntax": False,
        "paginationMode": "ITERATION",
    }

    try:
        resp = requests.post(TED_SEARCH_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("TED-Abfrage fehlgeschlagen: %s", exc)
        return []
    except ValueError:
        logger.warning("TED-Antwort war kein gültiges JSON.")
        return []

    raw_notices = data.get("notices") or data.get("results") or []
    results = []
    for n in raw_notices:
        pub_number = n.get("publication-number") or n.get("publicationNumber")
        if not pub_number:
            continue
        title = n.get("notice-title") or n.get("noticeTitle") or "(ohne Titel)"
        if isinstance(title, dict):  # mehrsprachiges Feld -> erste Sprache nehmen
            title = next(iter(title.values()), "(ohne Titel)")
        buyer = n.get("buyer-name") or n.get("buyerName") or ""
        if isinstance(buyer, dict):
            buyer = next(iter(buyer.values()), "")
        results.append(
            {
                "source": "TED (EU)",
                "id": f"ted-{pub_number}",
                "title": title,
                "buyer": buyer,
                "country": n.get("buyer-country") or n.get("buyerCountry") or "",
                "published": n.get("publication-date") or n.get("publicationDate") or "",
                "url": f"https://ted.europa.eu/en/notice/-/detail/{pub_number}",
            }
        )
    return results
