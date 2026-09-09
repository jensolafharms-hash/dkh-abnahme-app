# DJ Jensi – Sounds of Marbella 2026

Eine Sommernacht am Strand von Marbella, vom Abend bis zum Sonnenaufgang:
zehn Stücke, davon zwei kurze Zwischenspiele, rund 36 Minuten. Mediterran durch
Konzertgitarre, Trompete, Palmas, Cajón, Kastagnetten, Flöte und Steel Drum,
mit erkennbaren Anteilen von Deep House, House, Trance und Chill. Nichts
drängt sich vor; die Musik ist für den Hintergrund gedacht.

Jeder Titel hat eine eigene Geschichte, eine eigene Stimme, einen eigenen
Groove und eine eigene Form. Komposition und Arrangement stehen im Code.
Gitarre, Bass, Flöte, Trompete, Streicher, Chor, Percussion, Ney und Oud
kommen aus der frei lizenzierten Klangbibliothek FluidR3 (MIT-Lizenz) über
FluidSynth; Kick, Hats, Acid und Atmosphären werden synthetisiert. Keine
Loops, keine fremden Werke.

| Nr | Titel | Stil | Tonart | Geschichte und Signatur |
|----|-------|------|--------|-------------------------|
| 1 | Playa de Nagüeles, 9 p.m. | House, Acid, Chill | D dorisch | Ankunft am Strand. Wellen, Gitarre, Ney, House-Kick ab der ersten Minute. |
| 2 | La Concha Horizon | Deep House, Flamenco-Gitarre | G-Moll, andalusische Kadenz | Der Berg über der Bucht. Oud-Intro, Tremolo-Gitarre, Rasgueado-Break. |
| 3 | Golden Mile Breeze | Flamenco Chill, Bulería | A phrygisch-dominant | Abendspaziergang. 12er-Compás mit Kick auf den Akzenten, Palmas-Solo, Chor singt den Refrain. |
| 4 | Paseo | Zwischenspiel | A phrygisch-dominant | Oud, Gitarre, Zikaden, Darbuka von weitem. |
| 5 | Cabopino Drum Circle | Chill, tribal | E-Moll | Trommler am Strand. Ney-Ruf, 16 Takte Trommel-Break, alles stoppt gleichzeitig. |
| 6 | Puerto Banús Nights | Deep House, Trance | H-Moll | Hafenlichter. Der einzige Synthesizer-Titel: Glocke, Aufbau, weicher Supersaw-Höhepunkt. |
| 7 | Sierra Blanca Drift | Ballade im 6/8 | E dorisch, Schluss in E-Dur | Wind vom Berg. Ohne House-Drums, Grillen, Höhepunkt erst am Ende in Dur. |
| 8 | Casco Antiguo Echoes | Shuffle House, Dub | Fis phrygisch | Gassen der Altstadt. Trompete, Gitarre und Ney im Dialog, Bruch in die Stille. |
| 9 | Farola | Zwischenspiel | E phrygisch | Laterne, Glocke, Grillen, Streicher. |
| 10 | La Fontanilla Sunrise | Chill, Aufbau zum Sonnenaufgang | E phrygisch | Beginnt frei mit der Gitarrenphrase von Nr. 1, Tempo zieht an, Höhepunkt ganz am Ende. |

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
pip install numpy scipy lameenc pillow mido
apt install fluidsynth fluid-soundfont-gm
python3 album.py --sf           # alle Stücke mit Klangbibliothek nach ./out (Standard-Fassung)
python3 album.py --track 3 --sf # nur Stück 3
python3 album.py                # reine Synthese-Fassung ohne Klangbibliothek
python3 tag_mp3.py              # Tags und Cover in die MP3s
python3 make_cover.py           # Cover nach ./cover
```

Alles ist deterministisch: gleiche Datei, gleicher Seed, identisches Ergebnis.

## MIDI und Stems für die DAW

```bash
python3 album.py --export              # MIDI nach out/midi, Stems nach out/stems (MP3 320 kbit/s)
python3 album.py --export --stems-wav  # Stems als WAV (32 Bit float, ca. 600 MB je Titel)
```

- **MIDI** (`out/midi/*.mid`, Format 1): Spur 0 trägt Tempo-Map, Taktarten
  und Abschnittsmarker. Accelerando, Ritardando, 6/8 und der Bulería-Compás
  (als 12/8) werden je Takt als Tempo- und Taktwechsel geschrieben, damit die
  DAW das Raster korrekt anzeigt. Danach je Stimme eine Spur mit
  Programmwechsel und Velocity: Drums und Percussion auf Kanal 10 (GM-Noten),
  Bass, Sub, Gitarre (Melodie und Begleitung getrennt), Flöte, Trompete,
  Steel Drum, Chor, Pad, Chords, Acid, Arpeggio, Lead, Glocke.
- **Stems** (`out/stems/<titel>/`): alle 15 Spuren zeitgleich ab Sample 0,
  mit ihren Effekten und der Abschnittsdynamik, gemeinsam so verstärkt, dass
  ihre Summe dem Mix vor dem Master entspricht. Dazu `00-mix-master` und
  `tempo-map.txt` (Takt, Abschnitt, Taktart, BPM, Startzeit).
- Empfohlener Weg: MIDI in die DAW laden, die Spuren mit echten Instrumenten
  (Gitarren-Bibliothek, Drum-Kit, Bass) belegen, Stems als Referenz oder für
  Atmosphäre und Percussion behalten. Die Komposition bleibt dabei GEMA-frei.

Die MIDI-Dateien sind im Repository, die Stems wegen ihrer Größe nicht.

## Wie die Partitur aufgebaut ist

Ein Stück ist eine Liste von Abschnitten. Jeder Abschnitt legt Taktart, Tempo
(auch mit Übergang), Akkordfolge, Dynamik und die aktiven Stimmen fest:
Melodien mit Instrument und Register, Antwort-Instrument, Gitarrenbegleitung
(Anschlag, Rumba, Zupfmuster, 6/8-Arpeggio, Bulería-Rasgueado), Bass, Groove,
Hats, Percussion, Pad, Chor, Stabs, Acid, Arpeggio und Effekte (Riser, Wirbel,
Crash, Glocke, Schlussakkord). Die Themen stehen als Notation daneben:
Position, Halbton relativ zum Grundton, Dauer; je nach Taktart in Achteln
oder in Zählzeiten des Compás.

## Continuous Mix (55 bis 60 Minuten)

```bash
python3 mix.py             # rendert alle Teile (ca. 70 Minuten) und baut den Mix
python3 mix.py --only 3    # nur einen Teil neu rendern
python3 mix.py --remaster  # vorhandene ungemasterte Teile (NN-pre.wav) neu mastern und zusammensetzen
python3 mix.py --assemble  # nur zusammensetzen
```

`mix.py` baut aus der Album-Partitur eine durchgehend tanzbare Fassung:
verlängerte Groove-Teile, Tempo 118 bis 124 BPM, Golden Mile Breeze als
4/4-Rumba-House, Sierra Blanca Drift als Shuffle-House, Paseo mit Beat,
Farola als einzige Atempause. Jeder Teil endet mit acht Takten Beat-Ausklang
im Tempo des nächsten Teils und wird taktgenau überblendet (Bass des
ausgehenden Teils wird dabei ausgefiltert, Ein- und Ausstieg werden auf den
Pegel des Grooves angehoben). Drumlose Intros entfallen im Mix. Der Sub ist
ein sauberer Sinus in der Bass-Oktave (eigener Layer `sub`, kein
SoundFont-Ersatz). Club-Master: Tiefbass unter 45 Hz abgesenkt, Punch bei
60 bis 140 Hz, Buskompressor und Limiter mit Vorausschau (keine Sättigung).
Ergebnis in `out/mix/`: WAV, FLAC, MP3 320 kbit/s, MP3 192 kbit/s (im Repo),
MP3 64 kbit/s (WhatsApp) und `chapters.txt` mit den Kapitelmarken für die
YouTube-Beschreibung.

## Rechte

- ℗ & © 2026 DJ Jensi (Jens Olaf Harms). Alle Rechte vorbehalten, siehe `LICENSE`.
- Keine Samples, Loops oder Werke Dritter. Kompositionen und Arrangements
  sind hier notiert; Instrumentenklänge aus der Klangbibliothek FluidR3_GM
  (MIT-Lizenz), deren Nutzung in eigenen Produktionen frei ist.
- Die Titel sind bei keiner Verwertungsgesellschaft angemeldet. Wegen der
  GEMA-Vermutung dient dieses Repository mit Notation, Seeds und
  Git-Historie als Nachweis der Urheberschaft und GEMA-Freiheit.
- Für den Vertrieb: ISRC je Titel und UPC/EAN fürs Album vergibt der
  Distributor; für eine physische CD müssen nach EU-Produktsicherheits-
  verordnung Name, Postanschrift und E-Mail des Herstellers auf der
  Verpackung stehen (Zeile auf der Rückseite, Anschrift in `make_cover.py`).
