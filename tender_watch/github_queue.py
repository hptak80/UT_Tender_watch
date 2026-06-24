"""
Liest/schreibt state/pending_review.json im GitHub-Repo über die GitHub
Contents API - genutzt vom LOKALEN Skript (local_review.py), das keinen
Git-Checkout hat.

Benötigt ein GitHub Personal Access Token mit Lese-/Schreibrechten auf den
Repo-Inhalt (siehe README.md, Abschnitt "Lokale Nachbearbeitung").
"""
from __future__ import annotations

import base64
import json
import logging

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.github.com"
QUEUE_PATH_IN_REPO = "state/pending_review.json"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def fetch_pending(owner: str, repo: str, token: str, branch: str = "main") -> tuple[list[dict], str]:
    """Gibt (items, sha) zurück. sha wird für das spätere Zurückschreiben benötigt."""
    url = f"{API_BASE}/repos/{owner}/{repo}/contents/{QUEUE_PATH_IN_REPO}?ref={branch}"
    resp = requests.get(url, headers=_headers(token), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    items = json.loads(content).get("items", [])
    return items, data["sha"]


def write_pending(
    owner: str,
    repo: str,
    token: str,
    items: list[dict],
    sha: str,
    branch: str = "main",
) -> None:
    """Überschreibt state/pending_review.json mit der übergebenen (i.d.R. geleerten) Liste."""
    url = f"{API_BASE}/repos/{owner}/{repo}/contents/{QUEUE_PATH_IN_REPO}"
    new_content = json.dumps({"items": items}, ensure_ascii=False, indent=2)
    body = {
        "message": "Lokale Nachbearbeitung: Warteschlange aktualisiert [skip ci]",
        "content": base64.b64encode(new_content.encode("utf-8")).decode("ascii"),
        "sha": sha,
        "branch": branch,
    }
    resp = requests.put(url, headers=_headers(token), json=body, timeout=30)
    resp.raise_for_status()
