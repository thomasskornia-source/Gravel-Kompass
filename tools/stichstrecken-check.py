#!/usr/bin/env python3
"""Findet Stichstrecken (hin und zurück auf demselben Weg) in Touren.

Berechnet jede Etappe wie die Website über BRouter (gleiches Profil) und meldet Abschnitte,
die doppelt befahren werden. Aufruf:
    python3 tools/stichstrecken-check.py                # alle Touren
    python3 tools/stichstrecken-check.py <id> [<id>…]   # nur diese Touren
Exit-Code 1, wenn eine Stichstrecke über der Grenze gefunden wurde.
"""
import json, math, pathlib, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
GRENZE_M = 400      # doppelt befahrene Abschnitte ab dieser Länge melden
NAH_M = 20          # Abstand, ab dem zwei Trackpunkte als „derselbe Weg“ gelten
SCHRITT_M = 15      # Track wird in diesem Abstand neu abgetastet


def dist(a, b):
    R, t = 6371000, math.pi / 180
    dlat, dlon = (b[0] - a[0]) * t, (b[1] - a[1]) * t
    x = math.sin(dlat / 2) ** 2 + math.cos(a[0] * t) * math.cos(b[0] * t) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def route(wps, profil):
    profile = (profil if isinstance(profil, list) else [profil] if profil else ["gravel"]) + ["trekking"]
    lonlats = "|".join(f"{w[1]},{w[0]}" for w in wps)
    for p in profile:
        url = f"https://brouter.de/brouter?lonlats={lonlats}&profile={p}&alternativeidx=0&format=geojson"
        for _ in range(3):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    j = json.load(r)
                return [[c[1], c[0]] for c in j["features"][0]["geometry"]["coordinates"]]
            except Exception:
                time.sleep(2)
    raise RuntimeError("BRouter nicht erreichbar")


def resample(coords):
    out, rest = [coords[0]], 0.0
    for a, b in zip(coords, coords[1:]):
        d = dist(a, b)
        pos = SCHRITT_M - rest
        while pos <= d:
            f = pos / d
            out.append([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f])
            pos += SCHRITT_M
        rest = d - (pos - SCHRITT_M)
    return out


def doppelte_abschnitte(coords):
    pts = resample(coords)
    grid, doppelt = {}, [False] * len(pts)
    cell = 0.0004  # ~30-45 m
    for i, p in enumerate(pts):
        gx, gy = int(p[0] / cell), int(p[1] / cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((gx + dx, gy + dy), ()):
                    if j < i - 6 and dist(p, pts[j]) < NAH_M:
                        doppelt[i] = True
                        break
                if doppelt[i]:
                    break
            if doppelt[i]:
                break
        grid.setdefault((gx, gy), []).append(i)
    # zusammenhängende doppelte Stücke
    stuecke, start = [], None
    for i, d in enumerate(doppelt + [False]):
        if d and start is None:
            start = i
        elif not d and start is not None:
            laenge = (i - start) * SCHRITT_M
            if laenge >= GRENZE_M:
                stuecke.append((laenge, pts[start], pts[i - 1]))
            start = None
    return stuecke


def naechster_ort(p, wps):
    return min(wps, key=lambda w: dist(p, w))[2] if wps else "?"


def main(ids):
    files = [ROOT / "data" / "tours" / f"{i}.json" for i in ids] if ids else sorted((ROOT / "data" / "tours").glob("*.json"))
    fund = False
    for f in files:
        t = json.loads(f.read_text(encoding="utf-8"))
        tour_fund = False
        for n, e in enumerate(t["etappen"], 1):
            try:
                stuecke = doppelte_abschnitte(route(e["wegpunkte"], t.get("profil")))
            except Exception as err:
                print(f"?  {t['id']} Etappe {n}: nicht prüfbar ({err}) – später erneut prüfen")
                tour_fund = True
                continue
            for laenge, a, b in stuecke:
                fund = tour_fund = True
                print(f"⚠️  {t['id']} Etappe {n} ({e['von']} → {e['nach']}): {laenge/1000:.1f} km doppelt befahren "
                      f"bei {naechster_ort(a, e['wegpunkte'])} ({a[0]:.4f},{a[1]:.4f} bis {b[0]:.4f},{b[1]:.4f})")
        if not tour_fund:
            print(f"✓  {t['id']}")
    return 1 if fund else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
