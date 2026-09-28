#!/usr/bin/env python3
"""Repariert, was der Routen-Check an einer Tour findet – soweit das automatisch geht.

  - Stichstrecken: der Wegpunkt an der Spitze wird an den Abzweig gelegt (dort, wo die Sackgasse beginnt).
  - Hofeinfahrten, Privatwege, Fußwege, Treppen, Radverbote, Einbahnstraßen, Trails, Sand, grobe Wege,
    Schotter beim Rennrad, Campingplätze und Hofflächen: die Stelle kommt in "sperren" der Etappe
    (BRouter-Sperrkreis, die Website rechnet mit denselben Sperren) – der Routenplaner sucht sich einen anderen Weg.
  - Liegt eine solche Stelle an einem Wegpunkt, wird der Wegpunkt auf die Strecke ohne ihn verschoben.
Wiederholt, bis nichts mehr zu reparieren ist. Wird eine Etappe dadurch über 15 % länger, bleibt die letzte Runde
unberücksichtigt. Eintönige Abschnitte, Steigungen und Hauptstraßen bleiben Handarbeit (Wegpunkte neu planen).

Aufruf: python3 tools/routen-reparieren.py <tour-id> [<etappe-nr> …]   – schreibt die Tourdatei, danach
        python3 tools/routen-check.py <tour-id> und python3 tools/tours-index.py laufen lassen.
"""
import copy, importlib.util, json, math, pathlib, sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("rc", ROOT / "tools" / "routen-check.py")
rc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rc)

RADIUS_M = 15       # Sperrkreis
AM_WEGPUNKT_M = 60  # so nah an einem Wegpunkt wird nicht gesperrt, sondern der Wegpunkt verschoben
RUNDEN = 10
MEHR_KM = 1.15


def naechster(p, pts):
    return min(range(len(pts)), key=lambda i: rc.dist(p, pts[i][:2]))


OEFFENTLICH = {"residential", "unclassified", "tertiary", "secondary", "cycleway", "living_street"}


def oeffentlicher_punkt(p, weg_von):
    """Nächster Punkt auf einer öffentlichen Straße oder einem Radweg (OSM-Karte), mindestens weg_von m von p entfernt."""
    rc.karte([p])
    ky, kx = math.floor(p[0] / rc.KACHEL[0]), math.floor(p[1] / rc.KACHEL[1])
    best = None
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            rc.karte([((ky + dy + .5) * rc.KACHEL[0], (kx + dx + .5) * rc.KACHEL[1])])
            datei = rc.CACHE / f"{ky + dy}_{kx + dx}.osm"
            if not datei.exists():
                continue
            root = ET.fromstring(datei.read_bytes())
            nodes = {n.get("id"): (float(n.get("lat")), float(n.get("lon"))) for n in root.iter("node")}
            for way in root.iter("way"):
                tags = {x.get("k"): x.get("v") for x in way.iter("tag")}
                if tags.get("highway") not in OEFFENTLICH or tags.get("access") in ("private", "no"):
                    continue
                for nd in way.iter("nd"):
                    q = nodes.get(nd.get("ref"))
                    if q and rc.dist(q, p) >= weg_von and (best is None or rc.dist(q, p) < rc.dist(best, p)):
                        best = q
    return best


def wegpunkt_verschieben(t, e, i, stelle):
    """Wegpunkt i auf die Strecke legen, die ohne ihn gefahren würde (falls sie nah vorbeiführt),
    sonst auf die nächste öffentliche Straße abseits der Problemstelle."""
    wps = e["wegpunkte"]
    f = rc.brouter([wps[i - 1], wps[i + 1]], t.get("profil"), e.get("sperren"))
    linie = [(c[1], c[0]) for c in f["geometry"]["coordinates"]]
    j = naechster(wps[i][:2], linie)
    q = linie[j] if rc.dist(wps[i][:2], linie[j]) < 1000 else oeffentlicher_punkt(wps[i][:2], rc.dist(wps[i][:2], stelle) + 40)
    if q and rc.dist(q, wps[i][:2]) < 1000:
        wps[i][0], wps[i][1] = round(q[0], 5), round(q[1], 5)
        return True
    return False


def runde(t, e):
    """Eine Reparaturrunde; True, wenn etwas geändert wurde."""
    km, hm, anteil, befunde, rep = rc.pruefe_etappe(t, 0, e, True)
    wps, geaendert = e["wegpunkte"], False
    for a, b in rep["stubs"]:
        i = naechster(a, wps)
        if 0 < i < len(wps) - 1 and rc.dist(a, wps[i][:2]) < 400:
            wps[i][0], wps[i][1] = round(b[0], 5), round(b[1], 5)
            geaendert = True
    sperren = e.setdefault("sperren", [])
    for art, p in rep["sperren"] + rep["flaechen"]:
        i = naechster(p, wps)
        if rc.dist(p, wps[i][:2]) < AM_WEGPUNKT_M:
            if 0 < i < len(wps) - 1 and wegpunkt_verschieben(t, e, i, p):
                geaendert = True
            continue
        if not any(rc.dist(p, s[:2]) < RADIUS_M for s in sperren):
            sperren.append([round(p[0], 6), round(p[1], 6), RADIUS_M])
            geaendert = True
    if not sperren:
        del e["sperren"]
    return km, geaendert


def main(args):
    tid, nummern = args[0], [int(a) for a in args[1:]]
    pfad = ROOT / "data" / "tours" / f"{tid}.json"
    t = json.loads(pfad.read_text(encoding="utf-8"))
    for n, e in enumerate(t["etappen"], 1):
        if nummern and n not in nummern:
            continue
        start_km = None
        for r in range(RUNDEN):
            vorher = copy.deepcopy(e)
            km, geaendert = runde(t, e)
            start_km = start_km or km
            if km > start_km * MEHR_KM:
                e.clear(); e.update(vorletzt)
                print(f"   Etappe {n}: Umweg zu groß ({km:.1f} statt {start_km:.1f} km) – letzte Runde verworfen")
                break
            vorletzt = vorher
            print(f"   Etappe {n}, Runde {r + 1}: {km:.1f} km, {len(e.get('sperren', []))} Sperren")
            if not geaendert:
                break
        pfad.write_text(json.dumps(t, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
