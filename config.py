"""
Zentrale Konfiguration für den Ausschreibungs-Watcher.

Hier passt du an, WORAUF gesucht wird. Alles andere (Versand, Speicherung,
Quellen-Anbindung) liegt im Ordner tender_watch/.
"""

# ---------------------------------------------------------------------------
# Schlüsselwörter (Volltextsuche). Bewusst zweisprachig (DE/EN), weil
# Ausschreibungen je nach Land/Plattform in unterschiedlichen Sprachen
# veröffentlicht werden. Füge gerne weitere Begriffe / Sprachen hinzu.
# ---------------------------------------------------------------------------
KEYWORDS = [
    # Ultraschallprüfung allgemein
    "ultrasonic testing",
    "ultrasonic inspection",
    "ultrasonic test system",
    "phased array",
    "Ultraschallprüfung",
    "Ultraschallprüfgerät",
    "Ultraschallprüfsystem",
    "zerstörungsfreie Prüfung",
    "non-destructive testing",
    "NDT equipment",
    # Eisenbahnradsätze
    "wheelset inspection",
    "railway wheel testing",
    "axle ultrasonic",
    "Radsatzprüfung",
    "Eisenbahnradsatz",
    # Rohre / Pipelines
    "pipe inspection",
    "pipeline inspection",
    "tube testing ultrasonic",
    "Rohrprüfung",
    # Schiffe
    "hull inspection",
    "ship hull testing",
    "vessel NDT",
    # Schweißnähte
    "weld inspection",
    "weld testing ultrasonic",
    "Schweißnahtprüfung",
]

# ---------------------------------------------------------------------------
# CPV-Codes (Common Procurement Vocabulary), als zusätzlicher, strukturierter
# Filter neben den Schlüsselwörtern.
#
# WICHTIG: Bewusst NUR der eine, spezifische Code. 71631000 (Technical
# inspection services), 71600000 (Technical testing, analysis and
# consultancy services) und 38540000 (Testing/analysis machinery) wurden
# nach einem Testlauf wieder entfernt - sie sind so breit, dass sie auch
# Mikroskope, KFZ-Hauptuntersuchungen, Elektroprüfungen nach DGUV V3 oder
# Wasserbau-Ausschreibungen mit reinziehen. Lieber wenige, passende Treffer
# als 220 größtenteils irrelevante.
# ---------------------------------------------------------------------------
CPV_CODES = [
    "71632200",  # Non-destructive testing services
]

# ---------------------------------------------------------------------------
# Wie viele Tage zurück soll bei jedem Lauf gesucht werden? Sollte größer
# sein als dein Scan-Intervall (siehe .github/workflows/watch.yml), damit bei
# Ausfällen/Verzögerungen keine Treffer verloren gehen. Doppelte Treffer
# werden über state/seen.json ohnehin automatisch herausgefiltert.
# ---------------------------------------------------------------------------
LOOKBACK_DAYS = 10

# Quellen ein-/ausschalten
ENABLE_TED = True   # EU - Tenders Electronic Daily (kein API-Key nötig)
ENABLE_UK_FTS = True  # UK - Find a Tender Service (kein API-Key nötig)

# Soll der Cloud-Lauf (GitHub Actions) sofort eine Roh-Benachrichtigung
# schicken (vor der lokalen KI-Nachbearbeitung)? True = sofortige, aber
# ungefilterte/mehrsprachige Erstmeldung + später eine veredelte zweite
# Meldung von deinem PC. False = nur die veredelte lokale Meldung (dafür
# ggf. erst, wenn dein PC das nächste Mal läuft).
CLOUD_NOTIFY = True
