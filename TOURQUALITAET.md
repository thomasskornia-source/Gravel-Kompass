# Gravel Kompass – Tourqualität

Leitlinien für jede neue oder geänderte Tour. Sie wachsen mit jeder nachgefahrenen Tour:
Rückmeldungen von Thomas werden hier als allgemeine Regel festgehalten (Abschnitt „Aus gefahrenen Touren gelernt“).
Menschen fahren Rad vor allem für Naturerlebnis, Erholung, Bewegung und Genuss (ADFC-Radreiseanalyse) –
eine Tour soll deshalb **fließen**, unterwegs immer wieder Neues zeigen und nie zum Umdrehen zwingen.
Was jede Radart (Trekking, Gravel, Rennrad, MTB) von einer Tour braucht, steht in `RADFAHREN.md` und gilt mit.

## Grundregeln

1. **Nur öffentliche Wege – nie über Privatgrund.** Keine Hofeinfahrten, Bauernhöfe, Campingplätze, Firmen- oder
   Hotelgelände, Privatwege (`access=private/no`). Im Zweifel die öffentliche Straße nehmen.
2. **Keine Sackgassen und Stichstrecken.** Kein Weg wird hin und zurück gefahren – auch nicht 100 m in einen Ortskern.
   Runden sind echte Runden, Einwegtouren laufen vorwärts. Ausnahme nur, wenn am Ende etwas Lohnendes wartet (Gipfel,
   Aussicht, besonderer See, Sehenswürdigkeit) und es keinen Rundweg dorthin gibt – dann im Etappentext begründen.
3. **Wegpunkte liegen auf der Strecke**, nicht in Ortskernen, an Häusern oder Einfahrten. Der Routenplaner muss jeden
   Wegpunkt genau anfahren – ein Punkt neben der Strecke erzeugt eine Sackgasse. Orte, die seitlich liegen, weglassen.
4. **Offizielle, ausgeschilderte Radwege als Gerüst nutzen.** Gibt es für die Region eine Radroute (Seeumrundung,
   Flussradweg, Themenroute), die Wegpunkte direkt auf diese Route legen. Ziel: möglichst großer Anteil auf Radrouten
   (`tools/routen-check.py` zeigt den Anteil).
5. **Am Wasser bleiben.** Seeumrundungen und Flusstouren so ufernah wie möglich: Uferweg statt Hinterland, auch wenn es
   etwas länger ist.
6. **Natur statt Landstraße.** Liegt parallel zu einer Landstraße ein Radweg durch Wiesen, Moor oder Naturschutzgebiet,
   immer diesen nehmen. Straßen ohne Radweg nur, wenn es keine Alternative gibt – dann im Etappentext nennen.
7. **Abwechslung – nie länger als 30 Minuten dasselbe.** Kein halber oder ganzer Tag nur am selben Bach, Fluss oder
   Kanal entlang, nicht kilometerlang auf derselben Wegart oder schnurgerade neben einer Straße. Nach spätestens
   30 Minuten Fahrzeit soll sich etwas ändern: Richtung, Landschaft, Belag, ein Anstieg, ein Ort. Einen Flussradweg
   lieber in Stücken nutzen und zwischendurch über Hügel, Dörfer oder Wald ausweichen. Seeufer zählen nicht als
   eintönig. Dazu: Seeufer, Flusstäler, Wald, Aussichten, Kultur und gute Einkehr; ruhige Wege statt Hauptstraßen.
8. **Ehrliche Zahlen:** km und Höhenmeter aus dem Routenplaner (BRouter) übernehmen, nicht schätzen.
9. **Fahrradwege, keine Fußwege.** Fußwege, Fußgängerzonen und Treppen sind tabu, egal wie kurz – es ist eine
   Radtour. Erlaubt sind nur Wege mit Radfreigabe; Ausnahme ist nur das Queren einer Straße am Zebrastreifen.
10. **Rennrad nur auf Asphalt.** Keine Schotter-, Feld- oder Waldwege. Ruhige Landstraßen sind beim Rennrad gewollt;
   gemieden werden nur Bundesstraßen und stark befahrene Straßen.

## Prüfen vor dem Hochladen

`python3 tools/routen-check.py <tour-id>` muss ohne Befund durchlaufen (✓). Er meldet Stichstrecken ab 120 m,
Hofeinfahrten, Privatwege, Fußwege/Fußgängerzonen/Treppen ohne Radfreigabe, Hauptstraßen ohne Radweg ab 300 m
(Rennrad: nur Bundesstraßen), beim Rennrad unbefestigte Abschnitte, eintönige Abschnitte über 30 Minuten (am selben
Gewässer, dieselbe Wegart, ohne Abbiegen) sowie Campingplätze und Hofflächen aus der OpenStreetMap-Karte. Grenzen: Ein Hof, der in der Karte als öffentlicher Feldweg eingetragen ist,
fällt nicht auf – bei Wegen durch Einzelhöfe (Satellitenbild/Karte) lieber einen Umweg über die Straße wählen.

## Aus gefahrenen Touren gelernt

### Chiemsee-Umrundung (gefahren von Thomas, 27.09.2026)
- **Sackgassen in Grabenstätt, Chieming, Gollenshausen:** Wegpunkte lagen in Ortskernen bzw. auf Hauseinfahrten →
  Regel 2 und 3. Lösung: Wegpunkte direkt auf den offiziellen Chiemsee-Radweg gelegt.
- **Bauernhof bei Weisham, Campingplatz Kupferschmiede bei Arlaching:** Route führte über Privatgrund → Regel 1.
  Beim Campingplatz lag der ausgeschilderte Uferradweg direkt daneben.
- **Prien–Bernau und Chieming–Grabenstätt zu weit vom See / an der Landstraße:** Uferweg bzw. Radweg durchs
  Naturschutzgebiet Grabenstätter Moos wäre schöner gewesen → Regel 5 und 6.
- Ergebnis nach Überarbeitung: 63 km, rund drei Viertel auf ausgewiesenen Radrouten, keine Sackgasse, kein Privatgrund.

### Burgund ab Dijon (Rückmeldung von Thomas, 28.09.2026)
- **Ein ganzer Tag nur am Bach bzw. Kanal entlang** ist nervtötend → Regel 7: nach spätestens 30 Minuten muss sich
  etwas ändern. Der Routen-Check meldet solche Abschnitte jetzt als „eintönig“.
- **Fußwege sind bei einer Radtour nie erlaubt, auch nicht kurz** → Regel 9.
- **Rennrad fährt nur Asphalt, ruhige Landstraßen sind in Ordnung** → Regel 10.
