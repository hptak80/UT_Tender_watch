"""
Übersetzung, Stichwort-Extraktion und Relevanzprüfung über ein LOKALES
Modell via Ollama (z.B. Qwen, läuft bei dir über Hermes) - kein Tokenverbrauch,
keine Cloud-API, alles bleibt auf deinem Rechner.

Voraussetzung: Ollama läuft (Standard: http://localhost:11434) und das
gewünschte Modell ist bereits gezogen (`ollama list` zeigt dir den genauen
Tag, z.B. "qwen3:8b" - trag den exakten Tag in local_secrets.py ein).
"""
from __future__ import annotations

import json
import logging

import requests

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Du bewertest öffentliche Ausschreibungen für ein Unternehmen, \
das Ultraschallprüfsysteme / zerstörungsfreie Prüftechnik (NDT) anbietet, mit \
Schwerpunkt auf: Eisenbahnradsätze/Achsen, Rohre/Pipelines, Schiffe/Schiffsrümpfe, \
Schweißnähte, sowie allgemeine Ultraschall-/NDT-Prüfsysteme und -dienstleistungen.

Für jede Ausschreibung im JSON-Array entscheidest du:
- relevant: true, wenn es tatsächlich um Ultraschallprüfung, Phased-Array-Prüfung \
oder allgemeine zerstörungsfreie Werkstoffprüfung (NDT) von Bauteilen/Strukturen geht \
(Geräte, Systeme ODER Dienstleistungen). false bei Themen wie Software, allgemeine \
Bauarbeiten, Laborgeräte ohne NDT-Bezug, KFZ-Hauptuntersuchung, Elektroprüfung nach \
DGUV V3 ohne Ultraschallbezug, Mikroskope, Beleuchtung, u.ä.
- titel_de: kurzer, prägnanter deutscher Titel (max. 12 Wörter)
- stichworte: Array mit genau 3-5 deutschen Stichworten, die den Kern der \
Ausschreibung auf einen Blick erfassen (z.B. ["Ultraschall", "Schweißnaht", \
"Pipeline", "Wanddicke"])

Antworte AUSSCHLIESSLICH mit einem JSON-Array, keine Erklärungen, kein Markdown, \
kein Fließtext davor/danach. Format pro Element: \
{"id": "<id>", "relevant": true/false, "titel_de": "...", "stichworte": ["...", ...]}"""


def _call_ollama(batch: list[dict], ollama_url: str, model: str) -> list[dict]:
    payload_items = [
        {
            "id": item["id"],
            "title": item["title"],
            "buyer": item.get("buyer", ""),
            "country": item.get("country", ""),
            "source": item.get("source", ""),
        }
        for item in batch
    ]

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload_items, ensure_ascii=False)},
        ],
        "stream": False,
        # Viele Ollama-Modelle respektieren dieses Format-Flag und liefern
        # dann zuverlässiger reines JSON statt Fließtext.
        "format": "json",
    }

    try:
        resp = requests.post(f"{ollama_url}/api/chat", json=body, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data.get("message", {}).get("content", "").strip()
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()
        parsed = json.loads(raw_text)
        # Manche Modelle wickeln das Array in {"items": [...]} oder
        # {"results": [...]} ein - defensiv beide Formen akzeptieren.
        if isinstance(parsed, dict):
            for key in ("items", "results", "data"):
                if key in parsed:
                    return parsed[key]
        return parsed
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning(
            "Ollama-Aufruf fehlgeschlagen (läuft Ollama? Modellname korrekt?): %s", exc
        )
        return []


def review_items(items: list[dict], ollama_url: str, model: str, batch_size: int = 15) -> list[dict]:
    """Reichert Treffer um Übersetzung + Stichworte an und filtert irrelevante heraus.

    Schlägt der Ollama-Aufruf für einen Batch fehl, wird dieser Batch
    unverändert (ohne Übersetzung/Filterung) übernommen statt verworfen.
    """
    if not items:
        return items

    by_id = {item["id"]: item for item in items}
    enriched: list[dict] = []

    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        results = _call_ollama(batch, ollama_url, model)
        if not results:
            enriched.extend(batch)
            continue
        for r in results:
            item = by_id.get(r.get("id"))
            if not item:
                continue
            if not r.get("relevant", True):
                logger.info(
                    "Ollama-Filter: als nicht relevant eingestuft -> %s (%s)",
                    item["title"],
                    item["url"],
                )
                continue
            item = dict(item)
            item["title_de"] = r.get("titel_de") or item["title"]
            item["keywords"] = r.get("stichworte") or []
            enriched.append(item)

    return enriched
