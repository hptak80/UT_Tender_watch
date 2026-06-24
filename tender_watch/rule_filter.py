"""
Regelbasierter Vorfilter - kein KI, keine Tokenkosten, läuft überall.

Reduziert die durch CPV-Codes / Stichwörter entstehende Grundmenge, BEVOR
überhaupt benachrichtigt oder in die Warteschlange für die lokale
Ollama-Nachbearbeitung gelegt wird. Reine Textsuche (Negativliste).

Das ist bewusst simpel und nicht perfekt - z.B. wird eine Ausschreibung zur
"zerstörungsfreien Prüfung von Tragseilen für LED-Beleuchtung" hier evtl.
noch durchrutschen. Genau für solche Grenzfälle gibt es die zweite,
lokale KI-Prüfung (tender_watch/ollama_review.py).

Passe EXCLUDE_KEYWORDS hier nach Bedarf an, basierend auf den Falschtreffern,
die du in den Benachrichtigungen siehst.
"""
from __future__ import annotations

EXCLUDE_KEYWORDS = [
    # Häufige Falschtreffer aus dem ersten Testlauf
    "mikroskop", "microscope",
    "software", "informationssystem", "information system", "it-system",
    "kraftfahrzeug", "hauptuntersuchung", "roadworthiness", "vehicle inspection",
    "technische kontrole", "contrôle technique",
    "dguv v3", "ortsveränderlich",
    "vízmentesítés", "wasserableitung", "drainage", "génie civil",
    "beleuchtung", "led-leuchte", "lighting fixture", "seilhängeleuchte",
    "mérnöki tanulmány", "agent de commissionnement",
    # Ergänze hier weitere Begriffe, sobald dir Falschtreffer auffallen.
]


def passes_rule_filter(item: dict) -> bool:
    """True = Treffer behalten, False = aussortieren."""
    text = f"{item.get('title', '')} {item.get('buyer', '')}".lower()
    return not any(bad in text for bad in EXCLUDE_KEYWORDS)


def apply_rule_filter(items: list[dict]) -> list[dict]:
    return [item for item in items if passes_rule_filter(item)]
