# DJ Jensi – Sounds of Marbella 2026

Ein komplettes, **algorithmisch komponiertes und synthetisiertes** Chillout-Album
im Balearic-/Costa-del-Sol-Stil mit House-, Acid- und dezenten Trance-Elementen:
8 Tracks, je ca. 3:55 bis 4:30 Minuten (34 Minuten gesamt), erzeugt von einem
einzigen Python-Skript ohne Samples, Loops, Presets oder fremde Kompositionen.
Cover-Artwork (Front, Rückseite, CD-Inlay, Druck-PDF) entsteht ebenfalls
prozedural in `make_cover.py`.

| Nr | Titel                      | BPM | Tonart    | Charakter                                   |
|----|----------------------------|-----|-----------|---------------------------------------------|
| 1  | La Fontanilla Sunrise      | 98  | A minor   | Downtempo, Meeresrauschen, E-Piano, Lead                    |
| 2  | La Concha Horizon          | 106 | D dorian  | Soft House, dezente Acid-Line, Gitarre, Trance-Arp          |
| 3  | Golden Mile Breeze         | 112 | B minor   | Balearic House, Square-Acid, Stabs, Supersaw-Hook, Riser    |
| 4  | Cabopino Drum Circle       | 102 | G dorian  | Downtempo-Acid, Congas, Gitarre                             |
| 5  | Puerto Banús Nights        | 118 | A minor   | Deep/Acid House, Sidechain-Pads, Stabs, Trance-Hook         |
| 6  | Sierra Blanca Drift        | 94  | E major   | Sonniges Downtempo, Möwen, Gitarre                          |
| 7  | Casco Antiguo Echoes       | 110 | C minor   | Dub-House, Acid-Line, Stabs, E-Piano, Delays                |
| 8  | Playa de Nagüeles, 6 a.m.  | 96  | F dorian  | Sonnenaufgangs-Outro, Wellen, weiche Pads                   |

Fertige MP3s (192 kbit/s) liegen in `out/`, die Trackliste in `out/tracklist.json`.

## Selbst rendern

```bash
pip install numpy scipy lameenc
python3 generate_album.py            # alle Tracks nach ./out (MP3)
python3 generate_album.py --wav      # zusätzlich WAV (44,1 kHz / 16 Bit)
python3 generate_album.py --track 3  # nur einen Track
python3 generate_album.py --short    # Kurzfassung zum schnellen Anhören
```

Die Ausgabe ist deterministisch: gleicher Seed = identischer Track. Über die
`TRACKS`-Liste im Skript lassen sich Tempo, Tonart, Akkordfolge, Struktur und
Instrumentierung anpassen; ein neuer `seed` ergibt neue Melodien und Rhythmen.

## Wie der Klang entsteht

- **Drums/Percussion**: Kick aus einem Sinus mit Tonhöhen-Sweep, Hi-Hats,
  Claps, Shaker und Congas aus gefiltertem Rauschen bzw. gedämpften Sinustönen.
- **Bass**: Sinus-Subbass mit leichter Sättigung, per Sidechain zur Kick geduckt.
- **Pads**: fünf gegeneinander verstimmte Sägezahn-Oszillatoren pro Ton,
  langsam bewegtes Tiefpassfilter, Chorus-Verbreiterung, langer Hall.
- **E-Piano**: additive Synthese aus abklingenden Teiltönen.
- **Gitarre**: Karplus-Strong-Saitenmodell (Rauschimpuls in einen
  Feedback-Kammfilter).
- **Plucks/Lead**: Sägezahn/Rechteck mit Filterhüllkurve bzw. Sinus mit Vibrato.
- **Acid-Line (303-Stil)**: Sägezahn oder Rechteck durch ein zweipoliges
  Resonanzfilter mit abfallender Cutoff-Hüllkurve, Accent (lauter, offener,
  kürzer), Slide (Tonhöhen-Glide zur nächsten Note) und Sättigung. Die
  16-Schritt-Sequenz wird pro Track aus dem Seed erzeugt und über den Track
  variiert; im Build-Up öffnet das Filter.
- **House-Elemente**: Chord-Stabs (kurze, filtergeformte Akkorde auf Offbeats),
  metallische Open Hats aus unharmonischen Rechteckwellen, Four-on-the-Floor
  mit Sidechain.
- **Trance-Elemente (chillig dosiert)**: rollendes 16tel-Arpeggio aus hellen
  Plucks, breiter 7-fach-Supersaw-Hook mit langer Release in der zweiten Hälfte
  der Main-Parts, Noise-Riser mit aufsteigendem Filter im Build-Up
  (Tracks 2, 3 und 5).
- **Atmosphäre**: Wellenrauschen und Möwenrufe aus moduliertem Rauschen und
  gleitenden Sinustönen.
- **Komposition**: Akkordfolgen aus Stufen der jeweiligen Skala (Moll, Dorisch,
  Dur) mit 7ern/9ern; Melodiemotive entstehen als zufallsgesteuerte Bewegung in
  der Skala, die auf schweren Zählzeiten auf Akkordtöne einrastet und über den
  Track wiederholt/variiert wird.
- **Mix**: Hall per FFT-Faltung mit synthetischer Impulsantwort, Ping-Pong-Delays,
  Sidechain, Soft-Clipper, Normalisierung.

## Warum keine Samples aus House-/Acid-Platten?

Ein wiedererkennbares Sample aus einem fremden Recording braucht auch bei
wenigen Sekunden eine Freigabe von Label (Leistungsschutzrecht am Tonträger)
und Verlag (Urheberrecht an der Komposition), siehe „Metall auf Metall“
(BGH/EuGH). Deshalb werden hier die typischen Sounds (303-Acid, 909-Drums,
Chord-Stabs) selbst synthetisiert. Lizenzierte Royalty-free-Sample-Packs wären
grundsätzlich zulässig, passen aber schlecht zu einer CC0-Veröffentlichung und
sind nicht aus dem Skript nachweisbar.

## Rechtliche Einordnung (keine Rechtsberatung)

- **Keine fremden Werke**: Es werden weder Samples noch Loops, Presets,
  Melodien oder Songs Dritter verwendet. Alle Klänge werden aus mathematischen
  Grundfunktionen berechnet, alle Melodien und Akkordfolgen werden vom Skript
  erzeugt. Damit werden keine Urheber- oder Leistungsschutzrechte Dritter
  berührt.
- **GEMA**: Die Titel sind bei keiner Verwertungsgesellschaft angemeldet. In
  Deutschland gilt allerdings die sogenannte GEMA-Vermutung: Bei öffentlicher
  Wiedergabe wird zunächst angenommen, dass die GEMA die Rechte wahrnimmt. Wer
  die Musik öffentlich (Laden, Praxis, Veranstaltung, Telefonwarteschleife,
  Video) einsetzt, sollte deshalb nachweisen können, dass es sich um
  GEMA-freie Musik handelt. Dafür eignen sich dieses Repository (Skript +
  Seeds + Git-Historie) und die untenstehende Lizenz. Wer selbst
  GEMA-Mitglied ist, muss zusätzlich prüfen, ob eigene Werke automatisch
  eingebracht werden.
- **Lizenz der Ausgabe**: Rein maschinell erzeugte Werke ohne wesentlichen
  menschlichen Schöpfungsanteil genießen nach überwiegender Auffassung in
  Deutschland/EU keinen eigenen Urheberrechtsschutz. Um jede Unsicherheit
  auszuräumen, werden Skript und gerenderte Audiodateien hiermit unter
  **CC0 1.0 (Public Domain Dedication)** freigegeben. Sie dürfen ohne
  Nennung, ohne Lizenzgebühr und für jeden Zweck genutzt, bearbeitet und
  verbreitet werden.
- **Titel/Ortsnamen** sind geografische Bezeichnungen und keine Marken.
- **Streaming-Plattformen/Content-ID**: Wer die Tracks bei Spotify, YouTube
  o. Ä. hochlädt, sollte sie vorher nicht über einen Dritten mit Content-ID
  registrieren lassen, sonst könnten andere Nutzer der CC0-Dateien fälschlich
  Claims erhalten.

## Cover

```bash
pip install pillow
python3 make_cover.py
```

Erzeugt in `cover/`: `front.png` (3000 × 3000, Streaming/Digital), `front-1400.jpg`,
`back.png` (Rückseite mit Tracklist, Laufzeiten, Impressum), `cd-inlay-back.png`
(CD-Tray-Inlay 150 × 118 mm, 300 dpi, mit zwei Rücken) und `cover.pdf`
(Front 120 × 120 mm + Inlay, druckfertig). Das „J“ in „DJ Jensi“ ist wie
gewünscht spiegelverkehrt gesetzt. Die Laufzeiten werden aus den
Track-Definitionen berechnet und stimmen mit den MP3s überein.
Impressum-Daten stehen im Dictionary `IMPRESSUM` am Anfang von `make_cover.py`;
die Anschrift ist noch ein Platzhalter.

## Grenzen

Das ist synthetische Musik aus Grundwellenformen, kein produziertes Studioalbum
mit echten Instrumenten und Mastering. Der Klang ist bewusst reduziert
(Ambient/Lo-Fi-Lounge). Wer mehr Fülle möchte, kann im Skript Filter, Hallzeiten,
Layer-Pegel oder die Akkordfolgen verändern – alles bleibt dabei GEMA-frei.
