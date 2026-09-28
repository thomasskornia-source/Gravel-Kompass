#!/usr/bin/env python3
"""Repariert, was der Routen-Check an einer Tour findet – soweit das automatisch geht.

  - Stichstrecken: der Wegpunkt an der Spitze wird an den Abzweig gelegt (dort, wo die Sackgasse beginnt).
  - Hofeinfahrten, Privatwege, Fußwege, Treppen, Radverbote, Einbahnstraßen, Trails, Sand, grobe Wege,
    Schotter beim Rennrad, Campingplätze und Hofflächen: die Stelle kommt in "sperren" der Etappe
    (BRouter-Sperrkreis, die Website rechnet mit denselben Sperren) – der Routenplaner sucht sich einen anderen Weg.
  - Liegt eine solche Stelle an einem Wegpunkt, wird der Wegpunkt auf die Strecke ohne ihn verschoben.
Wiederholt, bis nichts mehr zu reparieren ist. Eine Änderung, die die Etappe über 15 % länger macht oder mehr als
500 m zusätzliche Hauptstraße ohne Radweg bringt, wird verworfen. Wegpunkte wandern höchstens 600 m. Eintönige Abschnitte, Steigungen und Hauptstraßen bleiben Handarbeit (Wegpunkte neu planen).

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
MAX_VERSCHIEBUNG_M = 600   # weiter wird ein Wegpunkt nie verschoben (das Ziel soll Ziel bleiben)
MAX_SACKGASSE_M = 1500     # Wegpunkt an der Spitze einer Sackgasse darf bis zum Abzweig wandern
MEHR_KM = 1.15
MEHR_STRASSE_M = 500   # mehr Hauptstraße ohne Radweg als vorher wird nicht in Kauf genommen


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


def kandidaten(t, e, original):
    """Vorgeschlagene Änderungen aus dem Routen-Check: ("wp", index, (lat, lon)) oder ("sperre", [lat, lon, r])."""
    km, hm, anteil, befunde, rep = rc.pruefe_etappe(t, 0, e, True)
    wps, sperren, out = e["wegpunkte"], e.get("sperren", []), []
    for a, b in rep["stubs"]:
        if rc.ausnahme(f"Stichstrecke bei {a[0]:.4f},{a[1]:.4f}", e.get("ausnahmen", [])):
            continue   # begründete Sackgasse (lohnendes Ziel) bleibt
        i = naechster(a, wps)
        if 0 < i < len(wps) - 1 and rc.dist(a, wps[i][:2]) < 400:
            out.append(("wp", i, (round(b[0], 5), round(b[1], 5)), "sackgasse"))
    for art, p in rep["sperren"] + rep["flaechen"]:
        i = naechster(p, wps)
        if rc.dist(p, wps[i][:2]) < AM_WEGPUNKT_M:
            if 0 < i < len(wps) - 1:
                probe = copy.deepcopy(e)
                if wegpunkt_verschieben(t, probe, i, p):
                    out.append(("wp", i, tuple(probe["wegpunkte"][i][:2])))
            continue
        if not any(rc.dist(p, s[:2]) < RADIUS_M for s in sperren):
            out.append(("sperre", [round(p[0], 6), round(p[1], 6), RADIUS_M]))
    return [c for c in out if c[0] != "wp" or
            rc.dist(c[2], original[c[1]]) <= (MAX_SACKGASSE_M if c[-1] == "sackgasse" else MAX_VERSCHIEBUNG_M)]


def schluessel(c):
    return (c[0], c[1], round(c[2][0], 4), round(c[2][1], 4)) if c[0] == "wp" else (c[0], round(c[1][0], 5), round(c[1][1], 5))


def anwenden(e, aenderungen):
    neu = copy.deepcopy(e)
    for c in aenderungen:
        if c[0] == "wp":
            neu["wegpunkte"][c[1]][0], neu["wegpunkte"][c[1]][1] = c[2]
        elif not any(rc.dist(c[1], s[:2]) < RADIUS_M for s in neu.get("sperren", [])):
            neu.setdefault("sperren", []).append(c[1])
    return neu


def schnell(t, e):
    """Länge (km) und Meter auf Hauptstraßen ohne Radweg (Abschnitte ab 300 m) – oder None, wenn nicht routbar."""
    try:
        f = rc.brouter(e["wegpunkte"], t.get("profil"), e.get("sperren"))
    except RuntimeError:
        return None
    m = f["properties"]["messages"]; h = m[0]; iD, iT = h.index("Distance"), h.index("WayTags")
    haupt = r"highway=(primary|trunk)\b" if rc.radart(t) == "road" else r"highway=(primary|secondary|trunk)\b"
    summe, lauf = 0, 0
    for r in m[1:] + [[0] * len(h)]:
        tags = str(r[iT])
        if rc.re.search(haupt, tags) and "cycleway" not in tags:
            lauf += int(r[iD])
        else:
            summe += lauf if lauf >= 300 else 0; lauf = 0
    return int(f["properties"]["track-length"]) / 1000, summe


def main(args):
    tid, nummern = args[0], [int(a) for a in args[1:]]
    pfad = ROOT / "data" / "tours" / f"{tid}.json"
    t = json.loads(pfad.read_text(encoding="utf-8"))
    for n in range(1, len(t["etappen"]) + 1):
        if nummern and n not in nummern:
            continue
        e = t["etappen"][n - 1]
        original = [w[:2] for w in e["wegpunkte"]]
        start = schnell(t, e)
        if not start:
            print(f"   Etappe {n}: nicht routbar – übersprungen"); continue
        grenze = (max(start[0], min(start[0] * MEHR_KM, t.get("etappeMaxKm", 9999))), start[1] + MEHR_STRASSE_M)
        ok = lambda q: q is not None and q[0] <= grenze[0] and q[1] <= grenze[1]
        abgelehnt = set()
        for r in range(RUNDEN):
            try:
                cands = [c for c in kandidaten(t, e, original) if schluessel(c) not in abgelehnt]
            except RuntimeError as err:
                print(f"   Etappe {n}: {err}"); break
            if not cands:
                break
            neu = anwenden(e, cands)
            if ok(schnell(t, neu)):
                e = neu
            else:   # einzeln probieren: nur übernehmen, was keinen Umweg und keine Hauptstraße bringt
                vorher = e
                for c in cands:
                    probe = anwenden(e, [c])
                    if ok(schnell(t, probe)):
                        e = probe
                    else:
                        abgelehnt.add(schluessel(c))
                if e is vorher:
                    break
            q = schnell(t, e)
            print(f"   Etappe {n}, Runde {r + 1}: {q[0]:.1f} km, {q[1]} m Hauptstraße, {len(e.get('sperren', []))} Sperren, "
                  f"{len(abgelehnt)} Vorschläge verworfen")
        t["etappen"][n - 1] = e
        pfad.write_text(json.dumps(t, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
