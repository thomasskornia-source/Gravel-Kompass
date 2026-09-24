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
   - **Anfrage** → recherchieren (Quellen aus `data/sources.json`), Tour in `data/tours.json` anlegen, Eintrag in `data/requests.json` (Name der anfragenden Person im Feld `name`, falls angegeben).
   - **Kommentar** → kleine Änderung direkt umsetzen und unter `aenderungen` der Tour dokumentieren (Datum, `von` = Name falls angegeben, Kommentar, Antwort); große Umbauten oder Fragen erst mit Thomas klären.
   - **Quelle** → Seite prüfen, bei Eignung in `data/sources.json` aufnehmen (alphabetisch).
3. Zeitstempel in `data/eingang-erledigt.json` eintragen.
4. Hochladen, Thomas kurz berichten, was erledigt ist und was offen bleibt.

## Regeln
- Namen von Anfragenden/Kommentierenden werden angezeigt, wenn sie angegeben wurden (`name` in requests.json, `von` in `aenderungen`); nur Vorname bzw. wie eingetragen, keine weiteren persönlichen Daten.
- Rennrad-Touren: `"profil": ["fastbike-lowtraffic", "fastbike"]`; Gravel ohne Profil (Standard gravel → trekking).
- Quellen der Recherche in `quellen` der Tour verlinken.

## Hochladen
Die Cloud-Sitzung darf nicht direkt nach GitHub pushen. Upload über Thomas' Mac:
Dateien nach `~/Dokumente/gravel-kompass/` schreiben, dann auf dem Mac in einen Klon von
`thomasskornia-source/Gravel-Kompass` kopieren, committen und pushen (GitHub-Token von Thomas nötig, wird nicht gespeichert).
