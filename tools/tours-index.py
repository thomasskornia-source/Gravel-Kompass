#!/usr/bin/env python3
"""Baut data/tours-index.json aus allen data/tours/<id>.json neu (neueste Tour zuerst)."""
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIELDS = ["id", "title", "subtitle", "createdAt", "land", "region", "saison", "tage",
          "fahrradtyp", "anspruch", "streckenform", "oberflaeche", "fuer", "profil"]

entries = []
for f in sorted((ROOT / "data" / "tours").glob("*.json")):
    raw = f.read_bytes()
    t = json.loads(raw)
    assert t["id"] == f.stem, f"{f.name}: id passt nicht zum Dateinamen"
    e = {k: t[k] for k in FIELDS if k in t}
    # Orte für die Suche, Wegpunkt-Koordinaten für Kachel-Skizze und Routen-Cache
    orte = []
    for st in t["etappen"]:
        for n in [st.get("von"), st.get("nach")] + [w[2] for w in st["wegpunkte"] if len(w) > 2]:
            if n and n not in orte:
                orte.append(n)
    e["orte"] = orte
    e["skizze"] = [[[w[0], w[1]] for w in st["wegpunkte"]] for st in t["etappen"]]
    # Stand der Datei: ändert sich bei jeder Änderung an der Tour (für „Neu“/„Geändert“ auf den Kacheln)
    e["stand"] = hashlib.sha1(raw).hexdigest()[:10]
    entries.append(e)

entries.sort(key=lambda e: (str(e.get("createdAt", "")), e["id"]), reverse=True)
out = ROOT / "data" / "tours-index.json"
out.write_text("[\n" + ",\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in entries) + "\n]\n", encoding="utf-8")
print(f"{len(entries)} Touren in {out.relative_to(ROOT)}")
