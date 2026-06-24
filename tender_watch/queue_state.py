"""
Warteschlange für die lokale KI-Nachbearbeitung (Ollama/Qwen).

Der Cloud-Lauf (GitHub Actions) legt hier jeden Treffer ab, der den
Regel-Filter passiert hat. Das lokale Skript (local_review.py) holt diese
Liste ab, lässt sie durch das lokale Modell prüfen/übersetzen, benachrichtigt
und leert die Warteschlange anschließend wieder.

Auf der Cloud-Seite (innerhalb desselben Checkouts) wird ganz normal mit
Dateizugriff gearbeitet - der GitHub-Actions-Workflow committed die Datei
am Ende wie auch state/seen.json. Das lokale Skript hat keinen Checkout und
nutzt daher die GitHub Contents API (siehe tender_watch/github_queue.py).
"""
from __future__ import annotations

import json
import os

QUEUE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "state", "pending_review.json"
)


def load_queue() -> list[dict]:
    if not os.path.exists(QUEUE_PATH):
        return []
    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("items", [])
    except (json.JSONDecodeError, OSError):
        return []


def save_queue(items: list[dict]) -> None:
    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump({"items": items}, f, ensure_ascii=False, indent=2)


def enqueue(new_items: list[dict]) -> None:
    """Fügt neue Treffer hinzu (dedupliziert nach id)."""
    existing = load_queue()
    existing_ids = {item["id"] for item in existing}
    for item in new_items:
        if item["id"] not in existing_ids:
            existing.append(item)
            existing_ids.add(item["id"])
    save_queue(existing)
