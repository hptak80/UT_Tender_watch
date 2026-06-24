# Tender Watch — Ausschreibungs-Beobachter für Ultraschallprüfsysteme

Sucht automatisch nach Ausschreibungen für Ultraschallprüfsysteme / zerstörungsfreie
Prüfung (Eisenbahnradsätze, Rohre, Schiffe, Schweißnähte, ...) und benachrichtigt
dich per **E-Mail und Telegram**, sobald eine neue passende Ausschreibung
veröffentlicht wird.

## Wie es funktioniert

Zwei Teile, die zusammenspielen - bewusst **ohne Cloud-KI, ohne Tokenkosten**:

**1. Cloud (GitHub Actions, alle 3 Stunden, läuft auch wenn dein PC aus ist)**
- Fragt **TED** (EU) und **UK Find a Tender Service** ab (beide offiziell,
  kostenlos, kein API-Key nötig).
- Wendet einen **regelbasierten Filter** an (Negativ-Stichwörter wie
  "Mikroskop", "Software", "KFZ-Hauptuntersuchung" fliegen raus) -
  reine Textlogik, kein KI, keine Tokenkosten, läuft überall.
- Schickt optional sofort eine Roh-Benachrichtigung (mehrsprachig,
  ungefiltert in der Tiefe) und legt jeden Treffer zusätzlich in eine
  Warteschlange (`state/pending_review.json`).

**2. Lokal (dein PC, `local_review.py`, läuft wann immer du willst/Ollama läuft)**
- Holt die Warteschlange von GitHub.
- Lässt **dein lokales Modell (Qwen über Ollama/Hermes)** jeden Treffer ins
  Deutsche übersetzen, mit 3-5 Stichworten versehen und nochmal auf
  thematische Relevanz prüfen - komplett lokal, **kostenlos, kein
  Tokenverbrauch**.
- Schickt eine zweite, "veredelte" Benachrichtigung nur für die wirklich
  passenden Treffer und leert danach die Warteschlange.

### Ehrlicher Hinweis zu "weltweit" und "sofort"

Es gibt **keine einzige globale Ausschreibungsdatenbank**. TED und UK Find a
Tender sind die beiden großen Quellen mit offener, kostenloser API. Für
weitere Märkte (USA/SAM.gov, UN/UNGM, Weltbank, einzelne Länder wie
Deutschland/evergabe-online) bräuchtest du zusätzliche Module — die Struktur
des Projekts (ein Python-Modul pro Quelle in `tender_watch/`) ist bewusst so
gebaut, dass sich das leicht ergänzen lässt. Sag Bescheid, wenn du eine
bestimmte Quelle ergänzt haben möchtest.

"Sofort" bedeutet in der Praxis: spätestens beim nächsten geplanten Lauf
(Standard: alle 3 Stunden). TED selbst veröffentlicht neue Notices ohnehin
nur an Werktagen, nicht in Echtzeit — engmaschigeres Polling bringt also nur
bis zu einem gewissen Punkt etwas.

## Einrichtung (einmalig, ca. 15 Minuten)

### 1. Repository auf GitHub anlegen

1. Gehe zu [github.com/new](https://github.com/new), lege ein neues
   **privates** Repository an (z. B. `tender-watch`).
2. Lade den Inhalt dieses Ordners hoch (z. B. per `git push` oder über
   "Upload files" im Browser — die komplette Ordnerstruktur inkl. `.github/`
   muss erhalten bleiben).

```bash
cd tender-watch
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/DEIN-USERNAME/tender-watch.git
git push -u origin main
```

### 2. Telegram-Bot einrichten (für Telegram-Benachrichtigungen)

1. In Telegram den Bot **@BotFather** öffnen, `/newbot` senden, einen Namen
   vergeben. Du erhältst ein **Bot-Token** (sieht aus wie
   `123456789:ABCdefGhIJKlmNoPQRstuVWXyz`).
2. Schreibe deinem neuen Bot eine beliebige Nachricht (z. B. "Hallo"), damit
   er dich kennt.
3. Rufe im Browser auf:
   `https://api.telegram.org/bot<DEIN-TOKEN>/getUpdates`
   und suche im JSON nach `"chat":{"id": ...}` — das ist deine **Chat-ID**.

### 3. E-Mail-Versand einrichten (z. B. mit Gmail)

1. In deinem Google-Konto unter **Sicherheit → App-Passwörter** ein neues
   App-Passwort erstellen (dafür muss 2-Faktor-Authentifizierung aktiv sein).
2. Notiere dir:
   - SMTP_HOST: `smtp.gmail.com`
   - SMTP_PORT: `587`
   - SMTP_USER: deine Gmail-Adresse
   - SMTP_PASS: das App-Passwort (nicht dein normales Passwort!)
   - EMAIL_TO: die Adresse, an die benachrichtigt werden soll (kann identisch sein)

   Jeder andere SMTP-Anbieter (z. B. dein Hoster, Outlook, etc.) funktioniert
   genauso — du brauchst nur Host/Port/Zugangsdaten.

### 4. Secrets in GitHub eintragen (für den Cloud-Teil)

Im Repository: **Settings → Secrets and variables → Actions → New repository
secret**. Lege folgende Secrets an (alle optional — was du nicht einträgst,
wird beim Versand einfach übersprungen):

| Secret-Name | Beispielwert |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `deine.adresse@gmail.com` |
| `SMTP_PASS` | `dein-app-passwort` |
| `EMAIL_TO` | `deine.adresse@gmail.com` |
| `TELEGRAM_BOT_TOKEN` | `123456789:ABC...` |
| `TELEGRAM_CHAT_ID` | `987654321` |

### 5. Lokale Nachbearbeitung einrichten (Ollama/Qwen über Hermes)

Das ist der zweite, kostenlose KI-Schritt - läuft komplett auf deinem PC.

1. **Python installieren** (falls noch nicht vorhanden): [python.org](https://www.python.org/downloads/)
   herunterladen, beim Setup "Add python.exe to PATH" anhaken.
2. **Repo lokal herunterladen**: Auf GitHub oben rechts bei "Code" auf
   "Download ZIP" klicken (oder `git clone`, falls du Git nutzt) und
   irgendwo auf deinem PC entpacken.
3. Im entpackten Ordner ein Terminal öffnen (Windows: im Ordner in die
   Adresszeile klicken, `cmd` eintippen, Enter) und ausführen:
   ```
   pip install requests
   ```
4. **GitHub Personal Access Token erstellen**: [github.com/settings/tokens](https://github.com/settings/tokens)
   → "Fine-grained tokens" → "Generate new token" → nur dein
   `tender-watch`-Repo auswählen → bei "Permissions" → "Contents" auf
   "Read and write" stellen → Token erstellen und kopieren (beginnt mit
   `github_pat_...`).
5. Die Datei `local_secrets.py.example` zu `local_secrets.py` umbenennen
   (im selben Ordner) und darin ausfüllen:
   - `GITHUB_OWNER`, `GITHUB_REPO`: dein GitHub-Username und Repo-Name
   - `GITHUB_TOKEN`: der Token aus Schritt 4
   - `OLLAMA_MODEL`: exakter Modell-Tag — im Terminal `ollama list`
     eingeben und den Namen von dort übernehmen (z. B. `qwen3:8b`)
   - `SMTP_*` / `TELEGRAM_*`: dieselben Werte wie bei den GitHub-Secrets
     (Telegram und/oder E-Mail, ganz wie du magst)

   ⚠️ **Diese Datei niemals zu GitHub hochladen** — sie enthält echte
   Zugangsdaten. Sie ist in `.gitignore` eingetragen, falls du Git nutzt.
6. Sicherstellen, dass **Ollama/Hermes läuft** und das Modell geladen ist.
7. Im Terminal im Projektordner ausführen:
   ```
   python local_review.py
   ```
   Du solltest Log-Zeilen sehen wie `X Treffer in der Warteschlange` und
   `X von Y Treffern als relevant eingestuft`.

**Automatisieren (optional):** Damit das regelmäßig läuft, solange dein PC
an ist, kannst du in der Windows-Aufgabenplanung ("Aufgabenplanung" /
"Task Scheduler") eine Aufgabe anlegen, die alle paar Stunden
`python local_review.py` im Projektordner ausführt. Ansonsten reicht es
auch, das Skript einfach von Zeit zu Zeit selbst zu starten.

### 6. Workflow aktivieren / testen

- Im Tab **Actions** des Repos sollte "Tender Watch" als Workflow auftauchen.
  Falls Actions deaktiviert sind: **Settings → Actions → General → Allow all
  actions**.
- Klicke auf **Run workflow**, um einen manuellen Testlauf zu starten, statt
  auf den nächsten geplanten Lauf zu warten.
- Schau dir das Log des Laufs an: Es zeigt, wie viele Treffer pro Quelle
  gefunden wurden und ob ggf. eine Quelle einen Fehler gemeldet hat.

Fertig — ab jetzt läuft die Überwachung automatisch.

## Anpassen

- **Suchbegriffe & CPV-Codes**: in `config.py` (`KEYWORDS`, `CPV_CODES`).
- **Zeitfenster pro Lauf**: `LOOKBACK_DAYS` in `config.py`.
- **Scan-Häufigkeit**: `cron`-Zeile in `.github/workflows/watch.yml`
  (Achtung: Zeiten sind in UTC).
- **Quellen ein-/ausschalten**: `ENABLE_TED` / `ENABLE_UK_FTS` in `config.py`.

## Lokal testen (optional, ohne GitHub Actions)

```bash
pip install -r requirements.txt
export SMTP_HOST=... SMTP_PORT=... SMTP_USER=... SMTP_PASS=... EMAIL_TO=...
export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...
python -m tender_watch.main
```

## Bekannte Grenzen

- TED's Such-API ändert gelegentlich Feldnamen/Syntax (eForms-Umstellung
  ist noch nicht überall abgeschlossen). Wenn `tender_watch/ted_source.py`
  plötzlich 0 Treffer liefert, lohnt ein Blick in
  [die Expert-Search-Doku](https://docs.ted.europa.eu/api/latest/search.html)
  bzw. in das [Swagger-Interface](https://api.ted.europa.eu/swagger-ui/index.html#/Search/search).
- Die UK-API filtert serverseitig nicht nach Stichwort/CPV — das Skript holt
  alle aktualisierten Tender-Releases im Zeitfenster und filtert lokal. Bei
  sehr großem `LOOKBACK_DAYS` kann das mehrere Sekunden dauern.
- Unterhalb der EU-Schwellenwerte veröffentlichte Ausschreibungen (z. B.
  viele deutsche Landes-/Kommunalausschreibungen) laufen oft nur über
  nationale Portale, nicht über TED. Für vollständige DACH-Abdeckung wäre
  ein zusätzliches Modul für z. B. bund.de/evergabe-online sinnvoll.
