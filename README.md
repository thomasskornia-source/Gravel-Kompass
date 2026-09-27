# Gravel Kompass

Persönliches Planungstool für mehrtägige Gravel-Touren, gemeinsam mit Claude gebaut.

- `index.html` – die Website (GitHub Pages)
- `data/tours/<id>.json` – je Tour eine Datei mit Etappen und Wegpunkten; die Route wird im Browser über BRouter bzw. OSRM (Fahrrad) auf echten Wegen berechnet
- `data/tours-index.json` – Kurzfassung aller Touren (neueste zuerst) für Übersicht und Suche; die Tourenseite lädt die einzelne Datei nach. Wird mit `python3 tools/tours-index.py` aus den Tour-Dateien neu gebaut
- `tools/stichstrecken-check.py` – prüft Touren auf Stichstrecken (hin und zurück auf demselben Weg)
- `data/sources.json` – Quellen-Datenbank für die Recherche
- `data/requests.json` – bisherige Tour-Anfragen
- `sw.js`, `.github/workflows/mitteilung.yml`, `tools/push-mitteilung.js` – Push-Mitteilung mit roter Zahl am App-Symbol bei jedem Push auf `main` (Secrets `VAPID_PRIVATE_KEY` und `PUSH_SUBSCRIPTIONS`)

Neue Anfragen und Quellen-Vorschläge: Formular ausfüllen, „senden“ öffnet das Teilen-Menü (WhatsApp, iMessage, Mail). Thomas leitet die Nachricht an Claude weiter.

Ablauf zum Abarbeiten von Anfragen und Kommentaren: siehe `ABLAUF.md`.
