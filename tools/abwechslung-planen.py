#!/usr/bin/env python3
"""Bricht eintönige Abschnitte auf (Regel 7 in TOURQUALITAET.md: nie länger als 20 Minuten dasselbe).

Für den längsten eintönigen Abschnitt einer Etappe werden Abstecher ausprobiert: Punkte 1, 2 und 3,5 km links und
rechts der Strecke, bei einem Viertel, der Hälfte und drei Vierteln des Abschnitts. Jeder Punkt wird als zusätzlicher
Wegpunkt eingefügt und die Etappe neu berechnet. Übernommen wird der Abstecher, der am meisten Eintönigkeit beseitigt –
aber nur, wenn die Etappe höchstens 15 % (mindestens 8 km) länger wird, nicht mehr als 500 m zusätzliche Hauptstraße ohne Radweg bekommt
und keine neue Sackgasse entsteht. Das wird wiederholt, solange es besser wird. Der neue Wegpunkt bekommt den Namen
des Ortes (OpenStreetMap/Nominatim).

Aufruf: python3 tools/abwechslung-planen.py <tour-id> [<etappe-nr> …]
Danach: python3 tools/routen-reparieren.py <tour-id>, python3 tools/routen-check.py <tour-id>, tools/tours-index.py
"""
import copy, importlib.util, json, math, pathlib, re, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("rc", ROOT / "tools" / "routen-check.py")
rc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rc)

MEHR_KM = 1.15
MEHR_STRASSE_M = 500
ABSTAENDE_M = (1000, 2000, 3500)
ANTEILE = (0.25, 0.5, 0.75)
MEHR_KM_MIN = 8   # kurze Etappen dürfen um bis zu 8 km wachsen
RUNDEN = 4


def bewerte(t, e):
    """Eintönigkeit (Meter über der Grenze), Länge, Hauptstraße und Sackgassen einer Etappe – oder None."""
    try:
        f = rc.brouter(e["wegpunkte"], t.get("profil"), e.get("sperren"))
    except RuntimeError:
        return None
    coords3 = [(c[1], c[0], c[2] if len(c) > 2 else 0) for c in f["geometry"]["coordinates"]]
    m = f["properties"]["messages"]; h = m[0]
    iL, iA, iD, iT = h.index("Longitude"), h.index("Latitude"), h.index("Distance"), h.index("WayTags")
    zeilen = [((int(r[iA]) / 1e6, int(r[iL]) / 1e6), r[iT]) for r in m[1:]]
    haupt = r"highway=(primary|trunk)\b" if rc.radart(t) == "road" else r"highway=(primary|secondary|trunk)\b"
    strasse, lauf = 0, 0
    for r in m[1:] + [[0] * len(h)]:
        tags = str(r[iT])
        if re.search(haupt, tags) and "cycleway" not in tags:
            lauf += int(r[iD])
        else:
            strasse += lauf if lauf >= 300 else 0; lauf = 0
    grenze = rc.TEMPO[rc.radart(t)] * 1000 * rc.LANGWEILIG_MIN / 60
    _, gewaesser = rc.karte([c[:2] for c in coords3])
    befunde = rc.eintoenig(coords3, zeilen, gewaesser, grenze)
    zuviel = sum(max(0, float(re.search(r"([\d.]+) km", b).group(1)) * 1000 - grenze) for b in befunde)
    stubs = sum(l for l, a, b in rc.stich.doppelte_abschnitte([list(c[:2]) for c in coords3]))
    return {"zuviel": zuviel, "befunde": befunde, "km": int(f["properties"]["track-length"]) / 1000,
            "strasse": strasse, "stubs": stubs, "coords3": coords3}


def ortsname(p):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&zoom=14&lat={p[0]}&lon={p[1]}&accept-language=de"
    try:
        time.sleep(1.1)
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "gravel-kompass-check"}), timeout=30) as r:
            a = json.load(r).get("address", {})
        return a.get("village") or a.get("hamlet") or a.get("town") or a.get("suburb") or a.get("city") or "Abstecher"
    except Exception:
        return "Abstecher"


def kandidaten(e, stand):
    """Abstecher-Punkte neben dem längsten eintönigen Abschnitt, jeweils mit Einfügestelle in den Wegpunkten."""
    pts, _ = rc.abtasten(stand["coords3"])
    laengster = max(stand["befunde"], key=lambda b: float(re.search(r"([\d.]+) km", b).group(1)))
    laenge = float(re.search(r"([\d.]+) km", laengster).group(1)) * 1000
    la, lo = map(float, re.search(r"ab (-?[\d.]+),(-?[\d.]+)", laengster).groups())
    i0 = min(range(len(pts)), key=lambda i: rc.dist(pts[i], (la, lo)))
    pos_wp = [min(range(len(pts)), key=lambda i: rc.dist(pts[i], w[:2])) for w in e["wegpunkte"]]
    out = []
    for anteil in ANTEILE:
        i = min(len(pts) - 8, i0 + int(laenge * anteil / rc.stich.SCHRITT_M))
        a, b = pts[max(0, i - 7)], pts[min(len(pts) - 1, i + 7)]
        k = math.cos(math.radians(a[0]))
        dy, dx = (b[0] - a[0]) * 111000, (b[1] - a[1]) * 111000 * k
        n = math.hypot(dx, dy) or 1
        for abstand in ABSTAENDE_M:
            for seite in (1, -1):
                # senkrecht zur Fahrtrichtung
                q = (pts[i][0] + seite * dx / n * abstand / 111000, pts[i][1] - seite * dy / n * abstand / (111000 * k))
                stelle = max(1, sum(1 for p in pos_wp if p <= i))
                if stelle >= len(e["wegpunkte"]):
                    continue
                out.append((stelle, (round(q[0], 5), round(q[1], 5))))
    return laengster, out


def main(args):
    tid, nummern = args[0], [int(a) for a in args[1:]]
    pfad = ROOT / "data" / "tours" / f"{tid}.json"
    t = json.loads(pfad.read_text(encoding="utf-8"))
    for n in range(1, len(t["etappen"]) + 1):
        if nummern and n not in nummern:
            continue
        e = t["etappen"][n - 1]
        start = bewerte(t, e)
        if not start or not start["befunde"]:
            print(f"   Etappe {n}: nichts Eintöniges"); continue
        grenze_km, grenze_str, stubs0 = min(max(start["km"] * MEHR_KM, start["km"] + MEHR_KM_MIN), max(start["km"], t.get("etappeMaxKm", 9999))), start["strasse"] + MEHR_STRASSE_M, start["stubs"]
        stand = start
        for r in range(RUNDEN):
            if not stand["befunde"]:
                break
            laengster, cands = kandidaten(e, stand)
            bestes = None
            for stelle, q in cands:
                probe = copy.deepcopy(e)
                probe["wegpunkte"].insert(stelle, [q[0], q[1], "?"])
                b = bewerte(t, probe)
                if (b and b["km"] <= grenze_km and b["strasse"] <= grenze_str and b["stubs"] <= stubs0 + 60
                        and b["zuviel"] < stand["zuviel"] - 500 and (not bestes or b["zuviel"] < bestes[1]["zuviel"])):
                    bestes = (probe, b, stelle, q)
            if not bestes:
                print(f"   Etappe {n}: kein passender Abstecher für „{laengster}“")
                break
            e, stand = bestes[0], bestes[1]
            e["wegpunkte"][bestes[2]][2] = ortsname(bestes[3])
            print(f"   Etappe {n}, Runde {r + 1}: Abstecher über {e['wegpunkte'][bestes[2]][2]} – {stand['km']:.1f} km, "
                  f"noch {stand['zuviel'] / 1000:.1f} km zu eintönig ({len(stand['befunde'])} Stellen)")
        t["etappen"][n - 1] = e
        pfad.write_text(json.dumps(t, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
