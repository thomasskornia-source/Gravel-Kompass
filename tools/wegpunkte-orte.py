#!/usr/bin/env python3
"""Legt Wegpunkte, die weiter als 1 km vom Ort ihres Namens (oder im Wasser) liegen, an den richtigen Ort.

  - Führt die Strecke ohnehin höchstens 900 m am Ortskern vorbei, wandert der Wegpunkt auf diesen Streckenpunkt
    (die Route bleibt praktisch gleich).
  - Sonst kommt der Wegpunkt in den Ort selbst (die Route ändert sich – danach tour-fertig.py laufen lassen).
  - Touren mit fester Spur (eigene Aufzeichnung): nur der erste Fall; verfehlt die Spur den Ort, wird der Wegpunkt
    nach dem Ort benannt, durch den die Spur dort wirklich führt.
Gleiche Punkte (Etappenziel = nächster Start) werden gemeinsam verschoben.

Aufruf: python3 tools/wegpunkte-orte.py [<tour-id> …]   – ohne ID alle Touren; schreibt die Tourdateien und
        gibt aus, welche Etappen sich geändert haben (dann tools/tour-fertig.py <tour-id>).
"""
import importlib.util, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("rc", ROOT / "tools" / "routen-check.py")
rc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rc)

AUF_STRECKE_M = 900


def naechster(p, pts, von=0, bis=None):
    bis = len(pts) if bis is None else bis
    return min(range(von, bis), key=lambda i: rc.dist(p, pts[i]))


def an_land(q, pts, i):
    """q, oder der nächste Streckenpunkt daneben, der nicht im Wasser liegt."""
    for j in sorted(range(max(0, i - 40), min(len(pts), i + 40)), key=lambda j: abs(j - i)):
        if not rc.im_wasser(pts[j]):
            return pts[j]
    return q


def ortsname_an(p):
    try:
        a = rc._nominatim(f"reverse?format=jsonv2&lat={p[0]}&lon={p[1]}&zoom=14&accept-language=de").get("address", {})
    except Exception:
        return None
    return a.get("village") or a.get("hamlet") or a.get("town") or a.get("suburb") or a.get("city")


def tour(tid):
    pfad = ROOT / "data" / "tours" / f"{tid}.json"
    t = json.loads(pfad.read_text(encoding="utf-8"))
    spur = [tuple(p[:2]) for p in json.loads((ROOT / t["spur"]).read_text())["punkte"]] if t.get("spur") else None
    neu, geaendert = {}, set()   # alte Koordinate -> neue
    for n, e in enumerate(t["etappen"], 1):
        wps = e["wegpunkte"]
        pts = pos = None
        for i, w in enumerate(wps):
            alt = (w[0], w[1])
            if alt in neu:
                w[0], w[1] = neu[alt][:2]
                if len(neu[alt]) > 2:
                    w[2] = neu[alt][2]
                continue
            name = w[2] if len(w) > 2 else ""
            o = rc.ortskern(name, alt)
            wasser = rc.im_wasser(alt)
            if not wasser and (not o or rc.dist(o, alt) <= rc.ORT_MAX_M):
                continue
            if pts is None:   # Strecke erst berechnen, wenn ein Wegpunkt falsch liegt
                pts = spur or [(c[1], c[0]) for c in rc.brouter(wps, t.get("profil"), e.get("sperren"))["geometry"]["coordinates"]]
                pos = [naechster(v[:2], pts) for v in wps]
            von = pos[i - 1] if i > 0 else 0
            bis = pos[i + 1] + 1 if i + 1 < len(wps) else len(pts)
            if von >= bis:
                von, bis = 0, len(pts)
            ziel = o or alt
            j = naechster(ziel, pts, von, bis)
            if rc.dist(pts[j], ziel) <= AUF_STRECKE_M or (wasser and not o):
                q, wie = an_land(pts[j], pts, j), "auf die Strecke am Ort"
            elif spur:
                q = an_land(pts[pos[i]], pts, pos[i])
                name = ortsname_an(q) or name
                wie = f"umbenannt in „{name}“ (Spur führt nicht durch den Ort)"
            else:
                q, wie = o, "in den Ort (Route ändert sich)"
                geaendert.add(n)
            q = (round(q[0], 5), round(q[1], 5))
            print(f"   {tid} E{n}: „{w[2] if len(w) > 2 else ''}“ {alt[0]:.5f},{alt[1]:.5f} → {q[0]},{q[1]} – {wie}")
            neu[alt] = (q[0], q[1], name)
            w[0], w[1] = q
            if len(w) > 2:
                w[2] = name
    if neu:
        pfad.write_text(json.dumps(t, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return neu, geaendert


def main(args):
    ids = args or sorted(p.stem for p in (ROOT / "data" / "tours").glob("*.json"))
    for tid in ids:
        neu, geaendert = tour(tid)
        if geaendert:
            print(f"→  {tid}: Route geändert in Etappe {', '.join(map(str, sorted(geaendert)))} – tools/tour-fertig.py {tid}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
