# DJ Jensi – Sounds of Marbella 2026

Eine Sommernacht am Strand von Marbella, vom Abend bis zum Sonnenaufgang:
acht Titel und zwei Zwischenspiele, rund 40 Minuten. Mediterran durch
Konzertgitarre, Trompete, Palmas, Cajón, Kastagnetten, Flöte und Steel Drum,
mit erkennbaren Anteilen von Deep House, House, Trance und Chill. Nichts
drängt sich vor; die Musik ist für den Hintergrund gedacht.

Jeder Titel hat eine eigene Geschichte, eine eigene Stimme, einen eigenen
Groove und eine eigene Form. Alles ist im Code komponiert und gerendert, ohne
Samples, Loops, Presets oder fremde Werke.

| Nr | Titel | Stil | Tonart | Geschichte und Signatur |
|----|-------|------|--------|-------------------------|
| 1 | Playa de Nagüeles, 9 p.m. | Chill, Halftime | D dorisch | Ankunft am Strand. Wellen, Gitarre, ferner Chor, Flöte. Kein Höhepunkt, ein langsames Einatmen. |
| 2 | La Concha Horizon | Deep House | G-Moll, andalusische Kadenz | Der Berg über der Bucht. Gedämpfte Trompete, Deep-Chords, Bläser-Break nur mit Bass. |
| 3 | Golden Mile Breeze | Flamenco Chill, Bulería | A phrygisch-dominant | Abendspaziergang, ein Fest in der Ferne. 12er-Compás, Palmas-Solo, Chor singt den Refrain. |
| – | Paseo | Zwischenspiel | A phrygisch-dominant | Gitarre, Zikaden, ein Cajón von weitem. |
| 4 | Cabopino Drum Circle | Chill, tribal | E-Moll | Trommler am Strand. Melodie erst nach über einer Minute, 16 Takte Trommel-Break, alles stoppt gleichzeitig. |
| 5 | Puerto Banús Nights | Deep House, Trance | H-Moll | Hafenlichter. Der einzige Synthesizer-Titel: Hafenglocke, Aufbau, weicher Supersaw-Höhepunkt. |
| 6 | Sierra Blanca Drift | Ballade im 6/8 | E dorisch, Schluss in E-Dur | Wind vom Berg. Ohne House-Drums, Grillen, Höhepunkt erst am Ende mit Wechsel nach Dur. |
| 7 | Casco Antiguo Echoes | Shuffle House, Dub | Fis phrygisch | Gassen der Altstadt. Trompete und Gitarre im Dialog, Bruch in die Stille: Trompete allein mit Echo. |
| – | Farola | Zwischenspiel | E phrygisch | Laterne, Glocke, Grillen. |
| 8 | La Fontanilla Sunrise | Chill, Aufbau zum Sonnenaufgang | E phrygisch | Beginnt frei mit der Gitarrenphrase von Titel 1, das Tempo zieht langsam an, Höhepunkt ganz am Ende. |

Fertige MP3s (192 kbit/s, mit Tags und Cover) in `out/`, Trackliste in
`out/tracklist.json`, Cover in `cover/`.

## Dateien

- `album.py` – **das Album**: Partitur aller Stücke (Formen, Grooves, Takte,
  Themen, Instrumentierung, Atmosphären) und die Engine dazu: Taktarten 4/4,
  6/8 und Bulería-Compás, Tempowechsel, Halftime, Shuffle, Trommel-Break,
  Chor (Formantsynthese), gedämpfte Trompete, Glocke, Toms, Zikaden, Grillen.
- `compose_song.py` – Instrumente (Gitarre, Trompete, Flöte, Steel Drum,
  E-Bass, Cajón, Palmas, Kastagnetten), Akkordbibliothek, Voicing; enthält die
  frühere Vorstufe des Albums mit einheitlicher Songform.
- `generate_album.py` – Klangbibliothek (Oszillatoren, Filter, Hall, Delay,
  Drums, Synth-Bass, Pads, Acid, Stabs, Master-Kette).
- `make_cover.py` – Cover-Artwork; liest Titel und Laufzeiten aus `album.py`.
- `tag_mp3.py` – schreibt ID3-Tags samt Cover in die MP3s.
- `make_player.py` – Web-Player-Seiten mit eingebettetem Audio.

## Rendern

```bash
pip install numpy scipy lameenc pillow
python3 album.py                # alle Stücke nach ./out
python3 album.py --track 3      # nur Titel 3 (Zwischenspiele: 3.5 und 7.5)
python3 tag_mp3.py              # Tags und Cover in die MP3s
python3 make_cover.py           # Cover nach ./cover
```

Alles ist deterministisch: gleiche Datei, gleicher Seed, identisches Ergebnis.

## Wie die Partitur aufgebaut ist

Ein Stück ist eine Liste von Abschnitten. Jeder Abschnitt legt Taktart, Tempo
(auch mit Übergang), Akkordfolge, Dynamik und die aktiven Stimmen fest:
Melodien mit Instrument und Register, Antwort-Instrument, Gitarrenbegleitung
(Anschlag, Rumba, Zupfmuster, 6/8-Arpeggio, Bulería-Rasgueado), Bass, Groove,
Hats, Percussion, Pad, Chor, Stabs, Acid, Arpeggio und Effekte (Riser, Wirbel,
Crash, Glocke, Schlussakkord). Die Themen stehen als Notation daneben:
Position, Halbton relativ zum Grundton, Dauer; je nach Taktart in Achteln
oder in Zählzeiten des Compás.

## Rechtliche Einordnung (keine Rechtsberatung)

- Keine Samples, Loops, Presets, Melodien oder Songs Dritter. Alle Klänge
  werden berechnet, alle Themen und Akkordfolgen sind hier notierte eigene
  Kompositionen.
- Die Titel sind bei keiner Verwertungsgesellschaft angemeldet. Wegen der
  GEMA-Vermutung sollte bei öffentlicher Wiedergabe der Nachweis der
  GEMA-Freiheit vorliegen; dieses Repository mit Notation, Seeds und
  Git-Historie ist dieser Nachweis.
- Skript und gerenderte Audiodateien stehen unter **CC0 1.0** (siehe `LICENSE`).
