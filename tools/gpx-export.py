#!/usr/bin/env python3
"""Erzeugt feste GPX-Dateien je Tour unter data/gpx/ (für Komoot, Hammerhead, Wahoo, Garmin …).

    data/gpx/<id>.gpx              komplette Tour als eine durchgehende Strecke
    data/gpx/<id>-etappe-<n>.gpx   einzelne Etappen (nur bei mehreren Etappen)

Routing wie auf der Website über BRouter (Profil der Tour, sonst gravel; Ausweichprofil trekking; Sperren der Etappe).
Warum feste Dateien: Nur eine echte Datei mit Web-Adresse bietet iOS beim Teilen Komoot, Hammerhead und Garmin an –
eine von der Website erzeugte Datei landet nur bei Apps mit eigener Teilen-Erweiterung (WhatsApp, Drive …).
Nur Touren, deren Datei sich seit dem letzten Lauf geändert hat, werden neu berechnet
(Stand in data/gpx/stand.json). Aufruf: python3 tools/gpx-export.py [<id> …]   (--alle erzwingt alles)
"""
import hashlib, json, math, pathlib, sys, time, urllib.request
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "gpx"


def route(wps, profil, sperren=None):
    profiles = (profil if isinstance(profil, list) else [profil] if profil else ["gravel"]) + ["trekking"]
    lonlats = "|".join(f"{w[1]},{w[0]}" for w in wps)
    nogos = "&nogos=" + "|".join(f"{s[1]},{s[0]},{int(s[2]) if len(s) > 2 else 20}" for s in sperren) if sperren else ""
    for p in profiles:
        url = f"https://brouter.de/brouter?lonlats={lonlats}&profile={p}&alternativeidx=0&format=geojson{nogos}"
        for _ in range(3):
            try:
                with urllib.request.urlopen(url, timeout=90) as r:
                    j = json.load(r)
                return [(c[1], c[0], c[2] if len(c) > 2 else None) for c in j["features"][0]["geometry"]["coordinates"]]
            except Exception:
                time.sleep(2)
    raise RuntimeError("BRouter nicht erreichbar")


TOLERANZ_M = 2   # Punkte, die weniger als 2 m von der vereinfachten Linie abweichen, fallen weg


def vereinfachen(coords):
    """Douglas-Peucker: kleine Dateien laden auf dem Handy schnell (die Dateiansicht erscheint erst nach dem Laden)."""
    if len(coords) < 3:
        return coords
    k = math.cos(math.radians(coords[0][0]))
    xy = [(c[1] * 111320 * k, c[0] * 111320) for c in coords]
    behalten = [False] * len(coords); behalten[0] = behalten[-1] = True
    stapel = [(0, len(coords) - 1)]
    while stapel:
        a, b = stapel.pop()
        (ax, ay), (bx, by) = xy[a], xy[b]
        dx, dy = bx - ax, by - ay; n = math.hypot(dx, dy) or 1e-9
        best, idx = 0, None
        for i in range(a + 1, b):
            # Abstand zur Linie a–b; bei Rundtouren (a = b) Abstand zum Punkt a
            d = abs(dy * (xy[i][0] - ax) - dx * (xy[i][1] - ay)) / n if n > 1 else math.hypot(xy[i][0] - ax, xy[i][1] - ay)
            if d > best:
                best, idx = d, i
        if idx is not None and best > TOLERANZ_M:
            behalten[idx] = True
            stapel += [(a, idx), (idx, b)]
    return [c for c, k_ in zip(coords, behalten) if k_]


def gpx(name, trk_name, coords):
    pts = "\n".join(
        f'<trkpt lat="{la:.5f}" lon="{lo:.5f}">' + (f"<ele>{el:.0f}</ele>" if el is not None else "") + "</trkpt>"
        for la, lo, el in vereinfachen(coords))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1" creator="Gravel Kompass" xmlns="http://www.topografix.com/GPX/1/1">\n'
            f"  <metadata><name>{escape(name)}</name></metadata>\n"
            f"  <trk>\n    <name>{escape(trk_name)}</name>\n    <trkseg>\n{pts}\n    </trkseg>\n  </trk>\n</gpx>\n")


def main(args):
    OUT.mkdir(parents=True, exist_ok=True)
    stand_file = OUT / "stand.json"
    stand = json.loads(stand_file.read_text()) if stand_file.exists() else {}
    alle = "--alle" in args
    ids = [a for a in args if not a.startswith("--")]
    files = [ROOT / "data" / "tours" / f"{i}.json" for i in ids] if ids else sorted((ROOT / "data" / "tours").glob("*.json"))
    vorhanden = {f.stem for f in (ROOT / "data" / "tours").glob("*.json")}
    for f in files:
        raw = f.read_bytes()
        h = hashlib.sha1(raw).hexdigest()[:10]
        t = json.loads(raw)
        if not alle and stand.get(t["id"]) == h and (OUT / f"{t['id']}.gpx").exists():
            continue
        try:
            stages = [route(e["wegpunkte"], t.get("profil"), e.get("sperren")) for e in t["etappen"]]
        except Exception as err:
            print(f"⚠️  {t['id']}: {err}")
            continue
        for old in OUT.glob(f"{t['id']}-etappe-*.gpx"):
            old.unlink()
        joined = []
        for st in stages:
            joined += st[1:] if joined and st and joined[-1][:2] == st[0][:2] else st
        (OUT / f"{t['id']}.gpx").write_text(gpx(t["title"], t["title"] + " (komplett)", joined), encoding="utf-8")
        if len(stages) > 1:
            for n, (e, st) in enumerate(zip(t["etappen"], stages), 1):
                (OUT / f"{t['id']}-etappe-{n}.gpx").write_text(
                    gpx(f"{t['title']} – Etappe {n}", f"Etappe {n}: {e['von']} – {e['nach']}", st), encoding="utf-8")
        stand[t["id"]] = h
        print(f"✓  {t['id']} ({len(stages)} Etappe(n))")
    # GPX gelöschter Touren entfernen
    for g in OUT.glob("*.gpx"):
        tid = g.stem.split("-etappe-")[0]
        if tid not in vorhanden:
            g.unlink()
            stand.pop(tid, None)
    stand_file.write_text(json.dumps(stand, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
