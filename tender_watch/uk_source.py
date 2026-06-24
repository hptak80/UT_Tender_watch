"""
Quelle: UK Find a Tender Service (FTS) - britisches Ausschreibungsportal.

Offizielle, unauthentifizierte OCDS-API:
GET https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages
Doku: https://www.find-tender.service.gov.uk/apidocumentation/1.0/GET-ocdsReleasePackages

Diese API filtert NICHT serverseitig nach Stichwort/CPV (erlaubte Parameter
sind nur: stages, limit, cursor, updatedFrom, updatedTo). Wir holen daher
alle seit LOOKBACK_DAYS aktualisierten Tender-Releases und filtern lokal
nach Titel/Beschreibung/CPV-Code.
"""
from __future__ import annotations

import datetime as dt
import logging

import requests

from config import CPV_CODES, KEYWORDS, LOOKBACK_DAYS

logger = logging.getLogger(__name__)

FTS_URL = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"

KEYWORDS_LOWER = [k.lower() for k in KEYWORDS]


def _matches(title: str, description: str, cpv_ids: list[str]) -> bool:
    text = f"{title} {description}".lower()
    if any(kw in text for kw in KEYWORDS_LOWER):
        return True
    return any(code in CPV_CODES for code in cpv_ids)


def fetch_notices() -> list[dict]:
    since = (dt.datetime.utcnow() - dt.timedelta(days=LOOKBACK_DAYS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    params = {"stages": "tender", "limit": 100, "updatedFrom": since}

    results: list[dict] = []
    cursor = None
    pages_fetched = 0

    while True:
        if cursor:
            params["cursor"] = cursor
        try:
            resp = requests.get(FTS_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.warning("UK-FTS-Abfrage fehlgeschlagen: %s", exc)
            break
        except ValueError:
            logger.warning("UK-FTS-Antwort war kein gültiges JSON.")
            break

        for release in data.get("releases", []):
            tender = release.get("tender", {}) or {}
            title = tender.get("title", "") or ""
            description = tender.get("description", "") or ""
            classification = tender.get("classification", {}) or {}
            cpv_ids = [classification.get("id", "")] if classification else []
            for item in tender.get("items", []) or []:
                for extra in item.get("additionalClassifications", []) or []:
                    if extra.get("scheme") == "CPV":
                        cpv_ids.append(extra.get("id", ""))

            if not _matches(title, description, cpv_ids):
                continue

            ocid = release.get("ocid") or release.get("id")
            if not ocid:
                continue

            buyer = (release.get("buyer") or {}).get("name", "")
            results.append(
                {
                    "source": "UK Find a Tender",
                    "id": f"uk-{ocid}",
                    "title": title or "(ohne Titel)",
                    "buyer": buyer,
                    "country": "UK",
                    "published": release.get("date", ""),
                    "url": f"https://www.find-tender.service.gov.uk/Notice/{release.get('id', '')}",
                }
            )

        cursor = data.get("links", {}).get("next")
        pages_fetched += 1
        # Sicherheitsnetz gegen Endlos-Pagination bei sehr großem Zeitfenster.
        if not cursor or pages_fetched >= 20:
            break

    return results
