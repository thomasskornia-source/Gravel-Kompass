#!/usr/bin/env python3
"""Qualitäts-Check für Touren (Regeln siehe TOURQUALITAET.md).

Berechnet jede Etappe wie die Website über BRouter und meldet:
  - Stichstrecken / Sackgassen (doppelt befahrene Abschnitte ab 120 m)
  - Hofeinfahrten und Privatwege (service=driveway, access=private/no)
  - Fußwege ohne Radfreigabe
  - Hauptstraßen (primary/secondary) ohne Radweg, ab 300 m am Stück
  - Campingplätze, Hofflächen und Bauernhöfe auf der Strecke (aus der OpenStreetMap-Karte)
  - Anteil der Strecke auf ausgeschilderten Radrouten (Info)

Aufruf: python3 tools/routen-check.py <tour-id> [...]   (ohne ID: alle Touren; --ohne-karte überspringt den Kartencheck)
Exit-Code 1, wenn etwas beseitigt oder begründet werden muss.
"""
import importlib.util, json, math, pathlib, re, sys, time, urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("stich", ROOT / "tools" / "stichstrecken-check.py")
stich = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(stich)

UA = {"User-Agent": "gravel-kompass-routen-check"}
KACHEL = (0.01, 0.015)   # Größe der Kartenausschnitte (Grad), ca. 1 x 1 km


def brouter(wps, profil):
    profiles = (profil if isinstance(profil, list) else [profil] if profil else ["gravel"]) + ["trekking"]
    lonlats = "|".join(f"{w[1]},{w[0]}" for w in wps)
    for p in profiles:
        url = f"https://brouter.de/brouter?lonlats={lonlats}&profile={p}&alternativeidx=0&format=geojson"
        for _ in range(3):
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    return json.load(r)["features"][0]
            except Exception:
                time.sleep(2)
    raise RuntimeError("BRouter nicht erreichbar")


def dist(a, b):
    return math.dist((a[0] * 111000, a[1] * 111000 * math.cos(math.radians(a[0]))), (b[0] * 111000, b[1] * 111000 * math.cos(math.radians(a[0]))))


def inside(p, poly):
    c = False
    for i in range(len(poly)):
        a, b = poly[i], poly[i - 1]
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]:
            c = not c
    return c


OEFFENTLICH = re.compile(r"route_bicycle|highway=(residential|unclassified|tertiary|secondary|primary|cycleway|living_street)\b")


def privatflaechen(coords, wegtags):
    """Campingplätze und Hofflächen (OSM), durch die die Strecke führt.
    Hofflächen zählen nur, wenn der Weg dort weder öffentliche Straße noch Radroute ist
    (in Weilern ist die Hoffläche oft großzügig um die Dorfstraße gezeichnet)."""
    kacheln = sorted({(math.floor(p[0] / KACHEL[0]), math.floor(p[1] / KACHEL[1])) for p in coords})
    polys = []
    for ky, kx in kacheln:
        s, w = ky * KACHEL[0], kx * KACHEL[1]
        url = f"https://api.openstreetmap.org/api/0.6/map?bbox={w:.4f},{s:.4f},{w + KACHEL[1]:.4f},{s + KACHEL[0]:.4f}"
        for _ in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                    root = ET.fromstring(r.read())
                break
            except Exception:
                time.sleep(3)
        else:
            print(f"   (Kartenausschnitt {s:.3f},{w:.3f} nicht ladbar)")
            continue
        nodes = {n.get("id"): (float(n.get("lat")), float(n.get("lon"))) for n in root.iter("node")}
        for way in root.iter("way"):
            t = {x.get("k"): x.get("v") for x in way.iter("tag")}
            art = ("Campingplatz" if t.get("tourism") in ("camp_site", "caravan_site") else
                   "Hoffläche" if t.get("landuse") == "farmyard" else
                   "Privatgelände" if t.get("access") == "private" and t.get("landuse") else None)
            if art:
                poly = [nodes[x.get("ref")] for x in way.iter("nd") if x.get("ref") in nodes]
                if len(poly) > 3:
                    polys.append((art, t.get("name", ""), poly))
        time.sleep(0.5)
    treffer = {}
    for art, name, poly in polys:
        drin = [p for p in coords if inside(p, poly)]
        if art != "Campingplatz":
            drin = [p for p in drin if not OEFFENTLICH.search(wegtags(p))]
        if drin:
            treffer[(art, name, round(drin[0][0], 4), round(drin[0][1], 4))] = len(drin)
    return treffer


def pruefe_etappe(t, n, e, karte):
    f = brouter(e["wegpunkte"], t.get("profil"))
    coords = [(c[1], c[0]) for c in f["geometry"]["coordinates"]]
    m = f["properties"]["messages"]
    h = m[0]; iL, iA, iD, iT = h.index("Longitude"), h.index("Latitude"), h.index("Distance"), h.index("WayTags")
    befunde, rad, gesamt, strasse = [], 0, 0, []
    ende = (e["wegpunkte"][0][:2], e["wegpunkte"][-1][:2])
    for r in m[1:]:
        d, tags = int(r[iD]), r[iT]
        p = (int(r[iA]) / 1e6, int(r[iL]) / 1e6)
        gesamt += d
        if "route_bicycle" in tags:
            rad += d
        am_rand = min(dist(p, ende[0]), dist(p, ende[1])) < 150   # Start/Ziel selbst
        if re.search(r"access=(private|no)\b", tags) and "bicycle=yes" not in tags:
            befunde.append(f"Privatweg {d} m bei {p[0]:.4f},{p[1]:.4f}")
        elif "service=driveway" in tags and not am_rand:
            befunde.append(f"Hofeinfahrt {d} m bei {p[0]:.4f},{p[1]:.4f} (Sackgasse oder Privatgrund?)")
        elif "highway=footway" in tags and not re.search(r"bicycle=(yes|designated)", tags) and d > 30 and not am_rand:
            befunde.append(f"Fußweg ohne Radfreigabe {d} m bei {p[0]:.4f},{p[1]:.4f}")
        if re.search(r"highway=(primary|secondary)\b", tags) and "cycleway" not in tags:
            strasse.append(d)
        else:
            if sum(strasse) >= 300:
                befunde.append(f"{sum(strasse)} m Hauptstraße ohne Radweg vor {p[0]:.4f},{p[1]:.4f}")
            strasse = []
    for laenge, a, b in stich.doppelte_abschnitte([list(c) for c in coords]):
        befunde.append(f"Stichstrecke {laenge / 1000:.2f} km bei {stich.naechster_ort(a, e['wegpunkte'])} ({a[0]:.4f},{a[1]:.4f})")
    if karte:
        punkte = [((int(r[iA]) / 1e6, int(r[iL]) / 1e6), r[iT]) for r in m[1:]]
        def wegtags(p):
            return min(punkte, key=lambda q: (q[0][0] - p[0]) ** 2 + (q[0][1] - p[1]) ** 2)[1]
        for (art, name, la, lo), k in privatflaechen(coords, wegtags).items():
            befunde.append(f"{art} {name} wird durchfahren bei {la},{lo}".replace("  ", " "))
    km = int(f["properties"]["track-length"]) / 1000
    return km, round(rad / max(gesamt, 1) * 100), befunde


def main(args):
    karte = "--ohne-karte" not in args
    ids = [a for a in args if not a.startswith("--")]
    files = [ROOT / "data" / "tours" / f"{i}.json" for i in ids] if ids else sorted((ROOT / "data" / "tours").glob("*.json"))
    fehler = False
    for f in files:
        t = json.loads(f.read_text(encoding="utf-8"))
        for n, e in enumerate(t["etappen"], 1):
            try:
                km, anteil, befunde = pruefe_etappe(t, n, e, karte)
            except Exception as err:
                print(f"?  {t['id']} Etappe {n}: nicht prüfbar ({err})"); fehler = True; continue
            zeichen = "⚠️ " if befunde else "✓ "
            print(f"{zeichen} {t['id']} Etappe {n}: {km:.1f} km, {anteil} % auf Radrouten")
            for b in befunde:
                print(f"     - {b}")
            fehler = fehler or bool(befunde)
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
