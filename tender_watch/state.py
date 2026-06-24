"""
Sehr einfache Persistenz für bereits gemeldete Ausschreibungen.

Warum überhaupt? GitHub-Actions-Läufe sind "stateless" - jeder Lauf startet
in einer frischen Umgebung. Damit wir nicht bei jedem Lauf erneut alle
Treffer der letzten LOOKBACK_DAYS melden, merken wir uns gesehene IDs in
einer JSON-Datei im Repo (state/seen.json) und committen sie nach jedem
Lauf zurück (siehe .github/workflows/watch.yml).
"""
import json
import os

STATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state", "seen.json")


def load_seen() -> set:
    if not os.path.exists(STATE_PATH):
        return set()
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("seen_ids", []))
    except (json.JSONDecodeError, OSError):
        # Defensiv: lieber mit leerem State weiterlaufen als abzubrechen.
        return set()


def save_seen(seen_ids: set) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    # Begrenzen, damit die Datei nicht unendlich wächst (älteste IDs sind
    # ohnehin irrelevant, da ihre Ausschreibungen längst abgelaufen sind).
    trimmed = list(seen_ids)[-5000:]
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"seen_ids": trimmed}, f, ensure_ascii=False, indent=2)
