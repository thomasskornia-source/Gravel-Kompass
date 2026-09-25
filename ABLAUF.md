# Gravel Kompass – Ablauf „abarbeiten“

## Eingang
- Website-Formulare (Anfrage, Kommentar, Quellen-Vorschlag) schreiben per POST in ein Google-Formular.
- Antworten landen in der Google-Tabelle **„Gravel Kompass Eingang“** (Google Drive von Thomas).
- Spalten: `Zeitstempel | Typ | Name | Tour | Nachricht`
  - Typ = `Anfrage`, `Kommentar` oder `Quelle` (Zeilen mit Typ `Test` ignorieren)
  - Tour = Tour-ID bei Kommentaren
- Bereits erledigte Zeilen stehen (Zeitstempel) in `data/eingang-erledigt.json`.

## Auslöser
- Sofort: Ein Apps Script in der Tabelle (`apps-script/eingang-ausloeser.gs`) startet bei jeder neuen
  Formular-Antwort die Claude-Routine „Gravel Kompass täglich abarbeiten“ über ihren API-Auslöser.
  Der Schlüssel liegt nur in den Skripteigenschaften (`ROUTINE_TOKEN`), nicht im Repo.
- Kein fester Zeitplan. Nach jedem Lauf kommt eine Push-Nachricht der Claude-App („🚴 Neue Tour online: …“ bei neuen Touren).

## Abarbeiten
1. Tabelle lesen, alle Zeilen, deren Zeitstempel nicht in `data/eingang-erledigt.json` steht, sind offen.
2. Pro Eintrag:
   - **Anfrage** → recherchieren (Quellen aus `data/sources.json`), Tour als neue Datei `data/tours/<id>.json` anlegen (Dateiname = `id`), Index-Eintrag in `data/tours-index.json` ergänzen, Eintrag in `data/requests.json` (Name der anfragenden Person im Feld `name`, falls angegeben).
   - **Kommentar** → kleine Änderung direkt in `data/tours/<id>.json` umsetzen und unter `aenderungen` der Tour dokumentieren (Datum, `von` = Name falls angegeben, Kommentar, Antwort); große Umbauten oder Fragen erst mit Thomas klären.
   - **Quelle** → Seite prüfen, bei Eignung in `data/sources.json` aufnehmen (alphabetisch).
3. Zeitstempel in `data/eingang-erledigt.json` eintragen.
4. Hochladen, Thomas kurz berichten, was erledigt ist und was offen bleibt.

## Tourendaten
- Jede Tour liegt in `data/tours/<id>.json` (vollständig: Kopfdaten, `beschreibung`, `quellen`, `etappen`, `aenderungen`).
- `data/tours-index.json` enthält pro Tour nur die Kopfdaten (`id`, `title`, `subtitle`, `createdAt`, `land`, `region`,
  `saison`, `tage`, `fahrradtyp`, `anspruch`, `streckenform`, `oberflaeche`, ggf. `profil`) plus `orte` (für die Suche)
  und `skizze` (Wegpunkt-Koordinaten je Etappe für die Kachel-Karte) und `stand` (Prüfsumme der Tour-Datei, steuert
  „Neu“/„Geändert“ auf den Kacheln), neueste zuerst.
- Nach jeder Änderung an einer Tour (neue Tour, geänderte Kopfdaten oder Wegpunkte) den Index neu bauen:
  `python3 tools/tours-index.py`. Die Tourenseite selbst liest immer die einzelne Datei.

## Regeln
- Namen von Anfragenden/Kommentierenden werden angezeigt, wenn sie angegeben wurden (`name` in requests.json, `von` in `aenderungen`); nur Vorname bzw. wie eingetragen, keine weiteren persönlichen Daten.
- Rennrad-Touren: `"profil": ["fastbike-lowtraffic", "fastbike"]`; Gravel ohne Profil (Standard gravel → trekking).
- Quellen der Recherche in `quellen` der Tour verlinken.

## Hochladen
- Änderungen direkt auf `main` committen und pushen (Repo `thomasskornia-source/Gravel-Kompass`); die Cloud-Sitzung
  kann das selbst, der Umweg über Thomas' Mac ist nicht mehr nötig.
- Vorher `python3 tools/tours-index.py` laufen lassen, falls Touren geändert wurden.
- Jeder Push auf `main` schickt automatisch eine Push-Mitteilung (GitHub Action „Mitteilung bei Änderung“). Die erste
  Zeile der Commit-Nachricht ist der Mitteilungstext – daher kurz und verständlich auf Deutsch formulieren. Ändert ein Push
  genau eine Tour, lautet der Titel „🚴 Neue Tour: …“ bzw. „✏️ Tour geändert: …“ und die Mitteilung öffnet die Tour.
  Neues Gerät: in der App „Mitteilungen“ (Fußzeile) → Code ins Secret `PUSH_SUBSCRIPTIONS` (eine Zeile je Gerät).
- GitHub Pages ist nach 1–2 Minuten aktuell; danach Thomas kurz auf Deutsch berichten, was online ist
  (mit Link `https://thomasskornia-source.github.io/Gravel-Kompass/#tour/<id>`).
