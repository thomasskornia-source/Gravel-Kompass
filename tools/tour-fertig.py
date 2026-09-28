#!/usr/bin/env python3
"""Macht eine neue oder geänderte Tour fertig – ein Befehl statt vier, mit kurzer Ausgabe (spart Token).

Nacheinander: routen-reparieren.py → abwechslung-planen.py → routen-reparieren.py → Prüfung wie routen-check.py.
Die ausführlichen Ausgaben landen in /tmp/tour-fertig-<id>.log; hier erscheint nur je Etappe eine Zeile,
bei Befunden gruppiert nach Art (Anzahl, erste Stelle).

Aufruf: python3 tools/tour-fertig.py <tour-id> [--nur-pruefen]
Exit-Code 1, wenn offene Befunde bleiben (dann Wegpunkte von Hand ändern oder begründete Ausnahme eintragen).
"""
import collections, importlib.util, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("rc", ROOT / "tools" / "routen-check.py")
rc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rc)


def schritt(skript, tid, log):
    with open(log, "a") as f:
        f.write(f"\n=== {skript}\n"); f.flush()
        subprocess.run([sys.executable, "-u", str(ROOT / "tools" / skript), tid], stdout=f, stderr=subprocess.STDOUT)


def art(befund):
    b = befund.split(" bei ")[0].split(" ab ")[0].split(" vor ")[0]
    return re.sub(r"[\d.,]+ ?(m|km)\b ?", "", b).replace("Eintönig: ", "Eintönig ").strip(" :")


def main(args):
    tid = args[0]
    log = f"/tmp/tour-fertig-{tid}.log"
    if "--nur-pruefen" not in args:
        open(log, "w").close()
        for s in ("routen-reparieren.py", "abwechslung-planen.py", "routen-reparieren.py"):
            schritt(s, tid, log)
    t = json.loads((ROOT / "data" / "tours" / f"{tid}.json").read_text(encoding="utf-8"))
    offen, summe_km, summe_hm = False, 0, 0
    for n, e in enumerate(t["etappen"], 1):
        km, hm, anteil, befunde, _ = rc.pruefe_etappe(t, n, e, True)
        summe_km += km; summe_hm += hm
        rest = [b for b in befunde if not rc.ausnahme(b, e.get("ausnahmen", []))]
        gruppen = collections.OrderedDict()
        for b in rest:
            gruppen.setdefault(art(b), []).append(b)
        kopf = f"E{n} {e['von']} → {e['nach']}: {km:.0f} km, {hm} Hm, {anteil} % Radrouten"
        if not gruppen:
            print(f"✓  {kopf}")
            continue
        offen = True
        print(f"⚠️  {kopf}")
        for a, bs in gruppen.items():
            stelle = re.search(r"(-?\d+\.\d{3,}),\s?(-?\d+\.\d{3,})", bs[0])
            print(f"     {len(bs)}× {a}" + (f" (z. B. {stelle.group(1)},{stelle.group(2)})" if stelle else ""))
    spanne = rc.ANSPRUCH.get(t.get("anspruch"))
    if spanne and summe_km:
        q = summe_hm / summe_km
        ok = spanne[0] <= q <= spanne[1]
        offen = offen or not ok
        print(f"{'✓ ' if ok else '⚠️'} Anspruch „{t['anspruch']}“: {q:.1f} Hm/km ({summe_km:.0f} km, {summe_hm} Hm)")
    print(f"(Details: {log})")
    return 1 if offen else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
