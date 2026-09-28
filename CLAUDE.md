# Gravel Kompass – Hinweise für Claude

Zuerst `README.md` und `ABLAUF.md` lesen; für Touren gelten `TOURQUALITAET.md` und `RADFAHREN.md`.

## Arbeitsweise
- Änderungen direkt auf `main` committen und pushen, kurz auf Deutsch berichten, was online ist.
- Namen aus dem Formular dürfen auf der Seite stehen.
- Rennrad-Touren: `"profil": ["fastbike-lowtraffic", "fastbike"]`.
- Tour-Änderungen erst auf `main`, wenn `tools/routen-check.py` sie geprüft hat. Halbfertige Zwischenstände nie auf `main`.

## GPX-Knopf – so lassen, nicht „verbessern“ (Stand 28.09.2026, von Thomas auf dem iPhone bestätigt)
Der rote Knopf „GPX komplette Tour“ und die Links „GPX Etappe n“ rufen `navigator.share({title, url})` mit der
**Internetadresse** der festen Datei `data/gpx/<id>.gpx` auf (Code: `gpxUrl()` und der Klick-Handler für `[data-gpx]`
in `index.html`). Das öffnet sofort das iOS-Teilen-Menü – genau wie „Tour teilen“ oben – und von dort geht die Tour
zu Hammerhead & Co. Ohne Teilen-Menü (Computer) wird die Datei heruntergeladen.

Die festen Dateien erzeugt die GitHub-Aktion `.github/workflows/gpx.yml` (`tools/gpx-export.py`) nach jedem Push, der
`data/tours/` ändert – mit den Sperren der Etappen und vereinfacht (2 m), damit sie klein bleiben.

Ausprobiert und gescheitert (nicht wieder einbauen):
- **Datei selbst teilen** (`navigator.share({files: [File]})`, egal welcher Dateityp): iOS zeigt dann nur Apps mit
  eigener Teilen-Erweiterung (WhatsApp, Drive, Nachrichten) – Hammerhead, Komoot, Garmin fehlen.
- **Datei im Browser öffnen** (`window.open`, Link mit `target=_blank`, auch über jsDelivr oder mit wechselnder
  Adresse): aus der Home-Bildschirm-App bleibt das Safari-Fenster weiß oder lädt beim zweiten Mal nicht mehr.
- **Menü mit mehreren Wegen** unter dem Knopf: unnötig kompliziert, von Thomas nicht gewollt.
