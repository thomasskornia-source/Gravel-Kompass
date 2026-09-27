#!/usr/bin/env python3
"""Erzeugt feste GPX-Dateien je Tour unter data/gpx/ (für Komoot, Hammerhead, Wahoo, Garmin …).

    data/gpx/<id>.gpx              komplette Tour als eine durchgehende Strecke
    data/gpx/<id>-etappe-<n>.gpx   einzelne Etappen (nur bei mehreren Etappen)

Routing wie auf der Website über BRouter (Profil der Tour, sonst gravel; Ausweichprofil trekking).
Nur Touren, deren Datei sich seit dem letzten Lauf geändert hat, werden neu berechnet
(Stand in data/gpx/stand.json). Aufruf: python3 tools/gpx-export.py [<id> …]   (--alle erzwingt alles)
"""
import hashlib, json, pathlib, sys, time, urllib.request
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "gpx"


def route(wps, profil):
    profiles = (profil if isinstance(profil, list) else [profil] if profil else ["gravel"]) + ["trekking"]
    lonlats = "|".join(f"{w[1]},{w[0]}" for w in wps)
    for p in profiles:
        url = f"https://brouter.de/brouter?lonlats={lonlats}&profile={p}&alternativeidx=0&format=geojson"
        for _ in range(3):
            try:
                with urllib.request.urlopen(url, timeout=90) as r:
                    j = json.load(r)
                return [(c[1], c[0], c[2] if len(c) > 2 else None) for c in j["features"][0]["geometry"]["coordinates"]]
            except Exception:
                time.sleep(2)
    raise RuntimeError("BRouter nicht erreichbar")


def gpx(name, trk_name, coords):
    pts = "\n".join(
        f'      <trkpt lat="{la:.6f}" lon="{lo:.6f}">' + (f"<ele>{el:.1f}</ele>" if el is not None else "") + "</trkpt>"
        for la, lo, el in coords)
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
            stages = [route(e["wegpunkte"], t.get("profil")) for e in t["etappen"]]
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
