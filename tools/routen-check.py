#!/usr/bin/env python3
"""Qualitäts-Check für Touren (Regeln siehe TOURQUALITAET.md).

Berechnet jede Etappe wie die Website über BRouter und meldet:
  - Stichstrecken / Sackgassen (doppelt befahrene Abschnitte ab 120 m)
  - Hofeinfahrten und Privatwege (service=driveway, access=private/no)
  - Radverbote (bicycle=no, Radwegbenutzungspflicht) und Einbahnstraßen gegen die Fahrtrichtung
  - Fußwege, Fußgängerzonen und Treppen ohne Radfreigabe (jede Länge; nur Zebrastreifen-Querungen bis 20 m nicht)
  - Hauptstraßen ohne Radweg ab 300 m am Stück (Rennrad: nur Bundesstraßen/primary – ruhige Landstraßen sind gewollt)
  - Eintönige Abschnitte, die länger als 20 Minuten dauern: immer am selben Gewässer entlang, immer dieselbe Wegart
    oder flach ohne Abbiegen geradeaus (Anstiege und Abfahrten gelten als Abwechslung)
  - Campingplätze, Hofflächen und Bauernhöfe auf der Strecke (aus der OpenStreetMap-Karte)
  - Gravel und Trekking: kein Sand, keine Trails (Gravel-Trails nur, wenn die Tour sie ausdrücklich anbietet);
    Trekking: keine groben Wege und keine Steigungen über 10 % (Schnitt über 200 m)
  - Rennrad: jeder unbefestigte Meter
  - Anspruch passend zu den Höhenmetern (Entspannt bis 6, Moderat 6–12, Anspruchsvoll über 12 Hm/km)
  - Anteil der Strecke auf ausgeschilderten Radrouten (Info)

Begründete Ausnahmen (z. B. Stichstrecke zum Gipfel) stehen in der Etappe:
  "ausnahmen": [{"lat": 49.32, "lon": 8.08, "grund": "Gipfel Kalmit – kein Rundweg"}]
Stichstrecken im Umkreis von 300 m zählen dann nicht (andere Befundart: "art": "Trail" o. Ä. dazuschreiben).

Gesperrte Stellen (damit der Routenplaner z. B. eine Hofeinfahrt meidet) stehen ebenfalls in der Etappe:
  "sperren": [[47.92, 12.35, 20]]   (lat, lon, Radius in m – die Website rechnet mit denselben Sperren)

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
CACHE = pathlib.Path.home() / ".cache" / "gravel-kompass-karte"
LANGWEILIG_MIN = 20      # so lange darf ein eintöniger Abschnitt höchstens dauern
TEMPO = {"road": 27, "mtb": 12, "trekking": 17, "gravel": 20}   # km/h für die Umrechnung Minuten -> Strecke
WASSER_M = 80            # so nah am Gewässer gilt als „am Wasser entlang“
WEGART = {"track": "Feld-/Waldweg", "path": "Weg", "cycleway": "Radweg", "unclassified": "Nebenstraße",
          "residential": "Wohnstraße", "tertiary": "Kreisstraße", "secondary": "Landstraße", "primary": "Bundesstraße"}
LUECKE_M = 400           # kürzere Unterbrechungen beenden einen eintönigen Abschnitt nicht
TRAIL = re.compile(r"mtb:scale=[1-6]|sac_scale=(?!hiking)|smoothness=(very_bad|horrible|very_horrible|impassable)")
NATURPFAD = re.compile(r"surface=(ground|dirt|earth|grass|rock|roots|mud)\b")
GROB_TREKKING = re.compile(r"tracktype=grade5|surface=(rock|mud|grass|pebblestone)\b")
MAX_STEIGUNG_TREKKING = 10   # %, auf mindestens 100 m
AUSNAHME_M = 300             # Befunde so nah an einer begründeten Ausnahme zählen nicht
ANSPRUCH = {"Entspannt": (0, 6), "Moderat": (6, 12), "Anspruchsvoll": (12, 99)}   # Hm pro km
UNBEFESTIGT = re.compile(r"surface=(gravel|fine_gravel|compacted|unpaved|dirt|ground|grass|sand|earth|mud|pebblestone|woodchips|rock)\b|tracktype=grade[2-5]")


def nogos(sperren):
    """Gesperrte Stellen einer Etappe ("sperren": [[lat, lon, radius_m], ...]) als BRouter-Parameter."""
    return "&nogos=" + "|".join(f"{s[1]},{s[0]},{int(s[2]) if len(s) > 2 else 20}" for s in sperren) if sperren else ""


def brouter(wps, profil, sperren=None):
    profiles = (profil if isinstance(profil, list) else [profil] if profil else ["gravel"]) + ["trekking"]
    lonlats = "|".join(f"{w[1]},{w[0]}" for w in wps)
    for p in profiles:
        url = f"https://brouter.de/brouter?lonlats={lonlats}&profile={p}&alternativeidx=0&format=geojson{nogos(sperren)}"
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


def karte(coords):
    """OSM-Kartenausschnitte entlang der Strecke laden (zwischengespeichert in ~/.cache)."""
    kacheln = sorted({(math.floor(p[0] / KACHEL[0]), math.floor(p[1] / KACHEL[1])) for p in coords})
    flaechen, gewaesser = [], []
    CACHE.mkdir(parents=True, exist_ok=True)
    for ky, kx in kacheln:
        s, w = ky * KACHEL[0], kx * KACHEL[1]
        datei = CACHE / f"{ky}_{kx}.osm"
        if not datei.exists():
            url = f"https://api.openstreetmap.org/api/0.6/map?bbox={w:.4f},{s:.4f},{w + KACHEL[1]:.4f},{s + KACHEL[0]:.4f}"
            for _ in range(3):
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                        datei.write_bytes(r.read())
                    break
                except Exception:
                    time.sleep(3)
            else:
                print(f"   (Kartenausschnitt {s:.3f},{w:.3f} nicht ladbar)")
                continue
            time.sleep(0.5)
        try:
            root = ET.fromstring(datei.read_bytes())
        except ET.ParseError:
            datei.unlink(); continue
        nodes = {n.get("id"): (float(n.get("lat")), float(n.get("lon"))) for n in root.iter("node")}
        for way in root.iter("way"):
            t = {x.get("k"): x.get("v") for x in way.iter("tag")}
            linie = [nodes[x.get("ref")] for x in way.iter("nd") if x.get("ref") in nodes]
            art = ("Campingplatz" if t.get("tourism") in ("camp_site", "caravan_site") else
                   "Hoffläche" if t.get("landuse") == "farmyard" else
                   "Privatgelände" if t.get("access") == "private" and t.get("landuse") else None)
            if art and len(linie) > 3:
                flaechen.append((art, t.get("name", ""), linie))
            if t.get("waterway") in ("river", "canal", "stream") and t.get("name"):
                gewaesser.append((t["name"], linie))   # Flüsse, Kanäle, Bäche; Seeufer zählen nicht
    return flaechen, gewaesser


def privatflaechen(coords, wegtags, flaechen):
    """Campingplätze und Hofflächen (OSM), durch die die Strecke führt.
    Hofflächen zählen nur, wenn der Weg dort weder öffentliche Straße noch Radroute ist
    (in Weilern ist die Hoffläche oft großzügig um die Dorfstraße gezeichnet)."""
    treffer = {}
    for art, name, poly in flaechen:
        drin = [p for p in coords if inside(p, poly)]
        if art != "Campingplatz":
            drin = [p for p in drin if not OEFFENTLICH.search(wegtags(p))]
        else:   # ausgeschilderte Radroute oder Radweg quer über das Gelände ist öffentlich
            drin = [p for p in drin if not re.search(r"route_bicycle|highway=cycleway|(?<![:\w])bicycle=designated", wegtags(p))]
        if drin:
            treffer[(art, name, round(drin[0][0], 4), round(drin[0][1], 4))] = len(drin)
    return treffer


def abstand_linie(p, a, b):
    k = math.cos(math.radians(p[0]))
    px, py, ax, ay, bx, by = p[1] * k, p[0], a[1] * k, a[0], b[1] * k, b[0]
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy or 1e-12)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy) * 111000


def abtasten(coords3):
    """Track alle SCHRITT_M Meter abtasten; liefert Punkte (lat, lon) und Höhen."""
    pts, hoehen, rest = [coords3[0][:2]], [coords3[0][2]], 0.0
    for a, b in zip(coords3, coords3[1:]):
        d = dist(a, b)
        pos = stich.SCHRITT_M - rest
        while pos <= d:
            f = pos / d
            pts.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)); hoehen.append(a[2] + (b[2] - a[2]) * f)
            pos += stich.SCHRITT_M
        rest = d - (pos - stich.SCHRITT_M)
    return pts, hoehen


def laengste_strecke(pts, bedingung):
    """Längster Abschnitt (m) der abgetasteten Punkte, in dem bedingung(i) gilt; Lücken bis LUECKE_M werden überbrückt."""
    best, start, zuletzt = (0, None), None, None
    for i in range(len(pts)):
        if bedingung(i):
            if start is None or (i - zuletzt) * stich.SCHRITT_M > LUECKE_M:
                start = i
            zuletzt = i
            laenge = (i - start) * stich.SCHRITT_M
            if laenge > best[0]:
                best = (laenge, pts[start])
    return best


def eintoenig(coords3, zeilen, gewaesser, grenze_m):
    """Abschnitte über grenze_m am selben Gewässer, auf derselben Wegart oder ohne Abbiegen.
    Wegart und Geradeaus zählen nur im Flachen – ein Anstieg oder eine Abfahrt ist Abwechslung."""
    pts, hoehen = abtasten(coords3)
    k = 20   # 300 m
    flach = [abs(hoehen[min(i + k, len(pts) - 1)] - hoehen[max(i - k, 0)]) < 18 for i in range(len(pts))]   # unter 3 %
    befunde = []
    # 1. am selben Gewässer entlang
    for name in {g[0] for g in gewaesser}:
        segs = [(a, b) for n, l in gewaesser if n == name for a, b in zip(l, l[1:])]
        grid = {}
        for a, b in segs:
            for q in (a, b):
                grid.setdefault((int(q[0] / 0.002), int(q[1] / 0.003)), []).append((a, b))
        def nah(i, grid=grid):
            p = pts[i]; g = (int(p[0] / 0.002), int(p[1] / 0.003))
            return any(abstand_linie(p, a, b) < WASSER_M for dx in (-1, 0, 1) for dy in (-1, 0, 1) for a, b in grid.get((g[0] + dx, g[1] + dy), ()))
        laenge, wo = laengste_strecke(pts, nah)
        if laenge > grenze_m:
            befunde.append(f"Eintönig: {laenge / 1000:.1f} km immer an „{name}“ entlang ab {wo[0]:.4f},{wo[1]:.4f}")
    # 2. dieselbe Wegart (highway-Klasse) am Stück
    art_bei = []
    for p, tags in zeilen:
        h = re.search(r"highway=(\w+)", tags)
        art_bei.append((p, h.group(1) if h else "?"))
    arten = [min(art_bei, key=lambda q: (q[0][0] - p[0]) ** 2 + (q[0][1] - p[1]) ** 2)[1] for p in pts[::4]]
    arten = [a for a in arten for _ in range(4)][:len(pts)]
    for art in set(arten):
        laenge, wo = laengste_strecke(pts, lambda i: i < len(arten) and arten[i] == art and flach[i])
        if laenge > grenze_m:
            befunde.append(f"Eintönig: {laenge / 1000:.1f} km flach immer auf {WEGART.get(art, art)} ab {wo[0]:.4f},{wo[1]:.4f}")
    # 3. ohne Abbiegen geradeaus (Richtungswechsel unter 45° auf 120 m)
    def richtung(a, b):
        return math.degrees(math.atan2((b[1] - a[1]) * math.cos(math.radians(a[0])), b[0] - a[0]))
    abbiegen = [False] * len(pts)
    for i in range(4, len(pts) - 4):
        d = abs((richtung(pts[i], pts[i + 4]) - richtung(pts[i - 4], pts[i]) + 180) % 360 - 180)
        abbiegen[i] = d > 45 or not flach[i]
    laenge, wo, start = 0, pts[0], 0
    for i in range(len(pts)):
        if abbiegen[i] or i == len(pts) - 1:
            if (i - start) * stich.SCHRITT_M > laenge:
                laenge, wo = (i - start) * stich.SCHRITT_M, pts[start]
            start = i
    if laenge > grenze_m:
        befunde.append(f"Eintönig: {laenge / 1000:.1f} km flach ohne Abbiegen geradeaus ab {wo[0]:.4f},{wo[1]:.4f}")
    return befunde


def radart(t):
    p = t.get("profil") or ""
    p = " ".join(p) if isinstance(p, list) else p
    typ = str(t.get("fahrradtyp", "")).lower()
    if "fastbike" in p or typ in ("road", "rennrad"):
        return "road"
    if "mtb" in p or typ in ("mtb", "mountainbike"):
        return "mtb"
    return "trekking" if "trekking" in p or typ == "trekking" else "gravel"


def steile_stuecke(coords3, grenze):
    """Abschnitte, die im Schnitt über 200 m steiler als grenze % sind (beide Richtungen; 200 m glätten Höhendaten)."""
    pts, hoehen = abtasten(coords3)
    k = 13   # 195 m
    out, start, maxi = [], None, 0
    for i in range(len(pts) - k):
        g = abs(hoehen[i + k] - hoehen[i]) / (k * stich.SCHRITT_M) * 100
        if g > grenze:
            start = i if start is None else start
            maxi = max(maxi, g)
        elif start is not None:
            out.append(((i + k - start) * stich.SCHRITT_M, round(maxi), pts[start])); start, maxi = None, 0
    return out


def pruefe_etappe(t, n, e, mit_karte):
    f = brouter(e["wegpunkte"], t.get("profil"), e.get("sperren"))
    coords = [(c[1], c[0]) for c in f["geometry"]["coordinates"]]
    index = {(round(c[0], 5), round(c[1], 5)): i for i, c in enumerate(coords)}
    coords3 = [(c[1], c[0], c[2] if len(c) > 2 else 0) for c in f["geometry"]["coordinates"]]
    m = f["properties"]["messages"]
    h = m[0]; iL, iA, iD, iT = h.index("Longitude"), h.index("Latitude"), h.index("Distance"), h.index("WayTags")
    rennrad = radart(t) == "road"
    haupt = re.compile(r"highway=(primary|trunk)\b" if rennrad else r"highway=(primary|secondary|trunk)\b")
    art_rad = radart(t)
    reparatur = {"sperren": [], "stubs": [], "flaechen": [], "strasse": [], "strasse_m": 0}
    befunde, rad, gesamt, strasse, schotter = [], 0, 0, [], []
    ende = (e["wegpunkte"][0][:2], e["wegpunkte"][-1][:2])
    zeilen, stellen, vorher = [], [], coords[0]

    def mitte(a, b):
        """Punkt mitten im Wegstück von a nach b (für eine Sperre, die nicht die Kreuzung trifft)."""
        i, j = index.get((round(a[0], 5), round(a[1], 5))), index.get((round(b[0], 5), round(b[1], 5)))
        if i is not None and j is not None and j - i >= 2:
            return coords[(i + j) // 2]
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

    def melde(art, d, p, zusatz=""):
        """Gleichartige Stellen im Abstand bis 200 m zu einem Befund zusammenfassen."""
        m_ = mitte(vorher, p)
        if stellen and stellen[-1][0] == art and dist(stellen[-1][3], p) < 200:
            stellen[-1][1] += d; stellen[-1][3] = p; stellen[-1][5].append(m_)
        else:
            stellen.append([art, d, p, p, zusatz, [m_]])

    for r in m[1:]:
        d, tags = int(r[iD]), r[iT]
        p = (int(r[iA]) / 1e6, int(r[iL]) / 1e6)
        if zeilen:
            vorher = zeilen[-1][0]
        zeilen.append((p, tags))
        gesamt += d
        if "route_bicycle" in tags:
            rad += d
        am_rand = min(dist(p, ende[0]), dist(p, ende[1])) < 150   # Start/Ziel selbst
        radfrei = re.search(r"(?<![:\w])bicycle=(yes|designated|permissive)", tags)
        fuss = (re.search(r"highway=(footway|pedestrian|steps)\b", tags) or
                re.search(r"highway=path\b", tags) and "foot=designated" in tags) and not radfrei
        if re.search(r"access=(private|no)\b", tags) and not re.search(r"(?<![:\w])bicycle=yes", tags):
            melde("Privatweg", d, p)
        elif "service=driveway" in tags and not am_rand:
            melde("Hofeinfahrt", d, p, " (Sackgasse oder Privatgrund?)")
        elif fuss and d > 0 and not ("footway=crossing" in tags and d <= 20) and min(dist(p, ende[0]), dist(p, ende[1])) > 50:
            art = "Treppe" if "highway=steps" in tags else "Fußgängerzone" if "highway=pedestrian" in tags else "Fußweg"
            melde(f"{art} ohne Radfreigabe", d, p)
        if re.search(r"(?<![:\w])bicycle=(no|use_sidepath)\b", tags) and not fuss:
            melde("Radverbot", d, p)
        if "reversedirection=yes" in tags and re.search(r"(?<![:\w])oneway=yes", tags) and "oneway:bicycle=no" not in tags:
            melde("Einbahnstraße gegen die Fahrtrichtung", d, p)
        if haupt.search(tags) and "cycleway" not in tags:
            strasse.append(d)
        else:
            if sum(strasse) >= 300:
                reparatur["strasse"].append(p); reparatur["strasse_m"] += sum(strasse)
                befunde.append(f"{sum(strasse)} m {'Bundesstraße' if rennrad else 'Hauptstraße'} ohne Radweg vor {p[0]:.4f},{p[1]:.4f}")
            strasse = []
        if rennrad and d > 0 and (UNBEFESTIGT.search(tags) or "highway=track" in tags and not re.search(r"surface=(asphalt|concrete|paved)", tags)):
            melde("Unbefestigt (Rennrad fährt nur Asphalt)", d, p)
        if art_rad in ("gravel", "trekking") and d > 0 and not fuss:
            gravel_trails = art_rad == "gravel" and "trail" in json.dumps(t.get("oberflaeche", "")).lower()
            if "surface=sand" in tags:
                melde("Sand", d, p)
            elif (not gravel_trails and not re.search(r"(?<![:\w])bicycle=designated|route_bicycle", tags)
                  and (TRAIL.search(tags) or "highway=path" in tags and NATURPFAD.search(tags))):
                melde("Trail", d, p)
            elif art_rad == "trekking" and GROB_TREKKING.search(tags):
                melde("Grober Weg (Trekking)", d, p)
    befunde += [f"{art} {d} m bei {a[0]:.4f},{a[1]:.4f}{z}" for art, d, a, _, z, _ in stellen]
    reparatur["sperren"] = [(art, mm) for art, _, _, _, _, mitten in stellen for mm in mitten]
    for laenge, a, b in stich.doppelte_abschnitte([list(c) for c in coords]):
        reparatur["stubs"].append((a, b))
        befunde.append(f"Stichstrecke {laenge / 1000:.2f} km bei {stich.naechster_ort(a, e['wegpunkte'])} ({a[0]:.4f},{a[1]:.4f})")
    if art_rad == "trekking":
        for laenge, g, a in steile_stuecke(coords3, MAX_STEIGUNG_TREKKING):
            befunde.append(f"Steil: {laenge} m mit bis zu {g} % (Trekking höchstens {MAX_STEIGUNG_TREKKING} %) bei {a[0]:.4f},{a[1]:.4f}")
    grenze_m = TEMPO[art_rad] * 1000 * LANGWEILIG_MIN / 60
    flaechen, gewaesser = karte(coords) if mit_karte else ([], [])
    befunde += eintoenig(coords3, zeilen, gewaesser, grenze_m)
    if mit_karte:
        def wegtags(p):
            return min(zeilen, key=lambda q: (q[0][0] - p[0]) ** 2 + (q[0][1] - p[1]) ** 2)[1]
        for (art, name, la, lo), k in privatflaechen(coords, wegtags, flaechen).items():
            reparatur["flaechen"].append((art, (la, lo)))
            befunde.append(f"{art} {name} wird durchfahren bei {la},{lo}".replace("  ", " "))
    km = int(f["properties"]["track-length"]) / 1000
    hm = int(f["properties"].get("filtered ascend", 0))
    return km, hm, round(rad / max(gesamt, 1) * 100), befunde, reparatur


def ausnahme(befund, ausnahmen):
    """Begründete Ausnahme (Etappenfeld "ausnahmen": [{"lat", "lon", "grund"}]) in der Nähe des Befunds?"""
    m = re.search(r"(-?\d+\.\d{3,}),\s?(-?\d+\.\d{3,})", befund)
    if not m:
        return None
    p = (float(m.group(1)), float(m.group(2)))
    for a in ausnahmen:   # gilt für Stichstrecken, außer "art" nennt eine andere Befundart
        if a.get("art", "Stichstrecke") in befund and dist(p, (a["lat"], a["lon"])) < AUSNAHME_M:
            return a.get("grund", "begründet")
    return None


def main(args):
    mit_karte = "--ohne-karte" not in args
    ids = [a for a in args if not a.startswith("--")]
    files = [ROOT / "data" / "tours" / f"{i}.json" for i in ids] if ids else sorted((ROOT / "data" / "tours").glob("*.json"))
    fehler = False
    for f in files:
        t = json.loads(f.read_text(encoding="utf-8"))
        summe_km = summe_hm = 0
        for n, e in enumerate(t["etappen"], 1):
            try:
                km, hm, anteil, befunde, _ = pruefe_etappe(t, n, e, mit_karte)
            except Exception as err:
                print(f"?  {t['id']} Etappe {n}: nicht prüfbar ({err})"); fehler = True; continue
            summe_km += km; summe_hm += hm
            offen = [b for b in befunde if not ausnahme(b, e.get("ausnahmen", []))]
            zeichen = "⚠️ " if offen else "✓ "
            print(f"{zeichen} {t['id']} Etappe {n}: {km:.1f} km, {hm} Hm, {anteil} % auf Radrouten")
            for b in befunde:
                grund = ausnahme(b, e.get("ausnahmen", []))
                print(f"     - {b}" + (f"  → Ausnahme: {grund}" if grund else ""))
            fehler = fehler or bool(offen)
        spanne = ANSPRUCH.get(t.get("anspruch"))
        if spanne and summe_km:
            quote = summe_hm / summe_km
            if not spanne[0] <= quote <= spanne[1]:
                print(f"⚠️  {t['id']}: Anspruch „{t['anspruch']}“ passt nicht – {quote:.1f} Hm/km "
                      f"(„{t['anspruch']}“ = {spanne[0]}–{spanne[1]} Hm/km)")
                fehler = True
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
