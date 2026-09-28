# Gravel Kompass

Persönliches Planungstool für mehrtägige Gravel-Touren, gemeinsam mit Claude gebaut.

- `index.html` – die Website (GitHub Pages)
- `data/tours/<id>.json` – je Tour eine Datei mit Etappen und Wegpunkten; die Route wird im Browser über BRouter bzw. OSRM (Fahrrad) auf echten Wegen berechnet
- `data/tours-index.json` – Kurzfassung aller Touren (neueste zuerst) für Übersicht und Suche; die Tourenseite lädt die einzelne Datei nach. Wird mit `python3 tools/tours-index.py` aus den Tour-Dateien neu gebaut
- `CLAUDE.md` – feste Hinweise für Claude (Arbeitsweise, GPX-Knopf: was funktioniert und was nicht)
- `TOURQUALITAET.md` – Regeln für gute Touren, wächst mit dem Feedback aus gefahrenen Touren
- `tools/tour-fertig.py` – ein Befehl, der eine Tour repariert, auflockert und prüft (kurze Ausgabe)
- `tools/routen-reparieren.py` – behebt Routen-Check-Befunde automatisch, soweit möglich (Sperren, Wegpunkte)
- `tools/abwechslung-planen.py` – bricht eintönige Abschnitte durch Abstecher auf (Regel 7)
- `RADFAHREN.md` – warum wir Rad fahren und was jede Radart von einer Tour braucht
- `tools/gpx-export.py` – feste GPX-Dateien je Tour/Etappe unter `data/gpx/` (läuft automatisch als GitHub-Aktion, wenn sich eine Tour ändert)
- `tools/routen-check.py` – Qualitäts-Check einer Tour (Stichstrecken, Privatgrund, Campingplätze, Hauptstraßen, Radrouten-Anteil); `tools/stichstrecken-check.py` wird davon genutzt
- `data/sources.json` – Quellen-Datenbank für die Recherche
- `data/requests.json` – bisherige Tour-Anfragen
- `sw.js`, `.github/workflows/mitteilung.yml`, `tools/push-mitteilung.js` – Push-Mitteilung mit roter Zahl am App-Symbol bei jedem Push auf `main` (Secrets `VAPID_PRIVATE_KEY` und `PUSH_SUBSCRIPTIONS`)

Neue Anfragen, Kommentare und Quellen-Vorschläge: Die Formulare schreiben über ein Google-Formular in die Tabelle
„Gravel Kompass Eingang“. Das Apps Script (`apps-script/eingang-ausloeser.gs`) prüft den Zugangscode (Skripteigenschaft
`ZUGANGSCODE`, Admin-Code `ADMIN_CODE`), trägt `ok`/`admin`/`gesperrt` ein und startet bei Freigabe sofort die
Claude-Routine (höchstens 20 Läufe pro Tag; Schlüssel nur in der Skripteigenschaft `ROUTINE_TOKEN`).
Push-Mitteilungen: neues Gerät in der App unter „Mitteilungen“ (Fußzeile) → Code ins Secret `PUSH_SUBSCRIPTIONS`.

Ablauf zum Abarbeiten von Anfragen und Kommentaren: siehe `ABLAUF.md`.
