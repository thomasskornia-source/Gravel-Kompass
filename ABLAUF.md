# Gravel Kompass – Ablauf „abarbeiten“

## Eingang
- Website-Formulare (Anfrage, Kommentar, Quellen-Vorschlag) schreiben per POST in ein Google-Formular.
- Antworten landen in der Google-Tabelle **„Gravel Kompass Eingang“** (Google Drive von Thomas).
- Spalten: `Zeitstempel | Typ | Name | Tour | Nachricht`
  - Typ = `Anfrage`, `Kommentar` oder `Quelle` (Zeilen mit Typ `Test` ignorieren)
  - Tour = Tour-ID bei Kommentaren
- Bereits erledigte Zeilen stehen (Zeitstempel) in `data/eingang-erledigt.json`.

## Abarbeiten
1. Tabelle lesen, alle Zeilen, deren Zeitstempel nicht in `data/eingang-erledigt.json` steht, sind offen.
2. Pro Eintrag:
   - **Anfrage** → recherchieren (Quellen aus `data/sources.json`), Tour in `data/tours.json` anlegen, Eintrag in `data/requests.json` (ohne Namen!).
   - **Kommentar** → kleine Änderung direkt umsetzen und unter `aenderungen` der Tour dokumentieren (Datum, Kommentar, Antwort); große Umbauten oder Fragen erst mit Thomas klären.
   - **Quelle** → Seite prüfen, bei Eignung in `data/sources.json` aufnehmen (alphabetisch).
3. Zeitstempel in `data/eingang-erledigt.json` eintragen.
4. Hochladen, Thomas kurz berichten, was erledigt ist und was offen bleibt.

## Regeln
- Keine Namen von Anfragenden auf der Website.
- Rennrad-Touren: `"profil": ["fastbike-lowtraffic", "fastbike"]`; Gravel ohne Profil (Standard gravel → trekking).
- Quellen der Recherche in `quellen` der Tour verlinken.

## Hochladen
Die Cloud-Sitzung darf nicht direkt nach GitHub pushen. Upload über Thomas' Mac:
Dateien nach `~/Dokumente/gravel-kompass/` schreiben, dann auf dem Mac in einen Klon von
`thomasskornia-source/Gravel-Kompass` kopieren, committen und pushen (GitHub-Token von Thomas nötig, wird nicht gespeichert).
