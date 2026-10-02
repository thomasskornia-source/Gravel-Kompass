#!/usr/bin/env python3
"""Übernimmt eine eigene Aufzeichnung (GPX, z. B. aus Komoot) als feste Spur einer Tour.

Schreibt data/spuren/<tour-id>.json: vereinfachte Originalgeometrie mit Höhen (ca. alle 25 m ein Punkt, Zeitstempel
werden verworfen) sowie km und Höhenmeter, berechnet aus der vollen Aufzeichnung. Die Tour verweist darauf mit
"spur": "data/spuren/<tour-id>.json"; Website, GPX-Export und Prüfwerkzeuge nutzen dann diese Spur statt Routing.
Gibt außerdem Orte entlang der Strecke aus (Nominatim), als Vorschlag für die Wegpunkte der Tour (Übersicht, Suche).

Aufruf: python3 tools/spur-import.py <datei.gpx> <tour-id> [--orte]
"""
import json, math, pathlib, sys, time, urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
ABSTAND_M = 25        # Punktabstand der vereinfachten Spur
HM_SCHWELLE_M = 4     # Höhenänderungen darunter gelten als Messrauschen (wie „filtered ascend“)


def dist(a, b):
    R, t = 6371000, math.pi / 180
    dlat, dlon = (b[0] - a[0]) * t, (b[1] - a[1]) * t
    x = math.sin(dlat / 2) ** 2 + math.cos(a[0] * t) * math.cos(b[0] * t) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def lesen(pfad):
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    root = ET.parse(pfad).getroot()
    pts = []
    for p in root.iterfind(".//g:trkpt", ns) or root.iterfind(".//trkpt"):
        e = p.find("g:ele", ns)
        pts.append((float(p.get("lat")), float(p.get("lon")), float(e.text) if e is not None else None))
    return pts


def hoehenmeter(pts):
    """Anstieg mit Schwelle: erst wenn es HM_SCHWELLE_M über dem letzten Tiefpunkt liegt, zählt es."""
    hoch, ref = 0.0, None
    for p in pts:
        if p[2] is None:
            continue
        if ref is None:
            ref = p[2]
        elif p[2] - ref >= HM_SCHWELLE_M:
            hoch += p[2] - ref; ref = p[2]
        elif p[2] < ref:
            ref = p[2]
    return round(hoch)


def vereinfachen(pts):
    out, seit = [pts[0]], 0.0
    for a, b in zip(pts, pts[1:]):
        seit += dist(a, b)
        if seit >= ABSTAND_M:
            out.append(b); seit = 0.0
    if out[-1] is not pts[-1]:
        out.append(pts[-1])
    return out


def ortsname(p):
    time.sleep(1.2)
    u = f"https://nominatim.openstreetmap.org/reverse?format=json&zoom=14&lat={p[0]}&lon={p[1]}&accept-language=de"
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "gravel-kompass-check"}), timeout=30) as r:
            a = json.load(r).get("address", {})
        return a.get("village") or a.get("town") or a.get("suburb") or a.get("hamlet") or a.get("city")
    except Exception:
        return None


def main(args):
    gpx, tid = args[0], args[1]
    pts = lesen(gpx)
    km = sum(dist(a, b) for a, b in zip(pts, pts[1:])) / 1000
    hm = hoehenmeter(pts)
    spur = vereinfachen(pts)
    ziel = ROOT / "data" / "spuren" / f"{tid}.json"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    daten = {"quelle": "eigene Aufzeichnung", "km": round(km, 1), "hm": hm,
             "punkte": [[round(p[0], 5), round(p[1], 5)] + ([round(p[2])] if p[2] is not None else []) for p in spur]}
    ziel.write_text(json.dumps(daten, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{ziel.relative_to(ROOT)}: {km:.1f} km, {hm} Hm, {len(spur)} von {len(pts)} Punkten")
    if "--orte" in args:   # alle ~6 km einen Ort nachschlagen
        orte, weiter = [], 0.0
        for a, b in zip(spur, spur[1:]):
            weiter += dist(a, b)
            if weiter >= 6000:
                weiter = 0.0
                n = ortsname(b)
                if n and (not orte or orte[-1][2] != n):
                    orte.append([round(b[0], 5), round(b[1], 5), n])
        print(json.dumps(orte, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
