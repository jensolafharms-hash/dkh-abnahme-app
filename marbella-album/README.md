# DJ Jensi – Sounds of Marbella 2026

Acht komponierte Titel im Balearic-House-Stil mit spanischen Einflüssen:
Konzertgitarre, Trompete, Palmas, Cajón, Kastagnetten, Flöte, Steel Drum,
dazu House-Drums, rollender Bass und punktuell Acid. Komplett im Code
komponiert und gerendert, ohne Samples, Loops, Presets oder fremde Werke.
Cover-Artwork (Front, Rückseite, CD-Inlay, Druck-PDF) entsteht ebenfalls
prozedural.

| Nr | Titel                      | BPM | Tonart / Modus                  | Charakter                                              |
|----|----------------------------|-----|---------------------------------|--------------------------------------------------------|
| 1  | La Fontanilla Sunrise      | 118 | E phrygisch                     | Sonnenaufgang, Flöte und Gitarre, Steel-Drum-Antworten |
| 2  | La Concha Horizon          | 122 | D-Moll, andalusische Kadenz     | Rumba-Gitarre, Trompete, Bläser-Stabs, Acid            |
| 3  | Golden Mile Breeze         | 124 | G mixolydisch                   | Festliche Rumba, Trompete, Palmas, Kastagnetten        |
| 4  | Cabopino Drum Circle       | 120 | A phrygisch-dominant            | Cajón, Congas, Palmas, Rasgueado, Acid                 |
| 5  | Puerto Banús Nights        | 122 | A-Moll                          | Nacht-House, Lead, Stabs, Acid, Supersaw am Höhepunkt  |
| 6  | Sierra Blanca Drift        | 118 | E dorisch                       | Träumerisch, Flöte, Gitarre, Steel Drum                |
| 7  | Casco Antiguo Echoes       | 124 | H phrygisch                     | Trompete und Gitarre im Dialog, Dub-Delays, Acid       |
| 8  | Playa de Nagüeles, 6 a.m.  | 116 | D dorisch                       | Frühmorgens am Strand, lange Coda mit Wellen           |

Fertige MP3s (192 kbit/s) liegen in `out/`, die Trackliste in `out/tracklist.json`,
das Cover in `cover/`.

## Dateien

- `compose_song.py` – **das Album**: Themen, Akkordfolgen, Songform, Instrumentierung
  aller acht Titel; modellierte Instrumente (Gitarre, Trompete, Flöte, Steel Drum,
  E-Bass, Cajón, Palmas, Kastagnetten).
- `generate_album.py` – Klangbibliothek (Oszillatoren, Filter, Hall, Delay,
  Drums, Bass, Pads, Acid, Stabs, Master-Kette). Der darin enthaltene ältere
  Loop-Generator wird für das Album nicht mehr benutzt.
- `make_cover.py` – Cover-Artwork; liest Titel, Tempi, Tonarten und Laufzeiten
  direkt aus `compose_song.py`.

## Rendern

```bash
pip install numpy scipy lameenc pillow
python3 compose_song.py            # alle Titel nach ./out (MP3)
python3 compose_song.py --track 3  # nur einen Titel
python3 compose_song.py --wav      # zusätzlich WAV
python3 make_cover.py              # Cover nach ./cover
```

Alles ist deterministisch: gleiche Datei, gleicher Seed, identisches Ergebnis.

## Wie ein Titel aufgebaut ist

Jeder Titel folgt einer Songform statt einer Loop-Textur:

1. **Intro** – Meer, Konzertgitarre spielt das Hauptthema frei im Tempo, Cajón
   und E-Bass setzen leise ein.
2. **Strophe 1 / 2** – House-Beat, rollender Bass, Hauptthema auf Flöte,
   Gitarre oder Trompete; ein zweites Instrument antwortet in die langen Töne
   hinein (Frage und Antwort).
3. **Refrain 1** – eigenes Refrain-Thema über eine andere Akkordfolge, Palmas,
   Bläser- oder House-Stabs.
4. **Strophe 3** – zurückgenommen, Gitarre (Tremolo oder Picado-Läufe), Acid
   wird präsenter.
5. **Refrain 2** – voller, Flöte verdoppelt.
6. **Zwischenteil** – Beat weg, Meer kommt hoch, nur ein Fragment des Themas,
   Stille, Riser, Snare-Roll.
7. **Höhepunkt** – Crash, Modulation einen Ganzton höher, Refrain-Thema mit
   Trompete/Flöte, Ride, Stabs; in der zweiten Hälfte antwortet das Hauptthema
   als Gegenstimme.
8. **Coda** – Hauptthema auf der Gitarre in der neuen Tonart, Tempo wird
   langsamer, Schlussakkord und Wellen.

Die Themen stehen als Notation in `compose_song.py` (Achtelposition, Halbton
relativ zum Grundton, Dauer). Modi: Phrygisch und phrygisch-dominant für den
spanischen Klang, andalusische Kadenz (i – VII – VI – V), Dorisch und
Mixolydisch für die helleren Titel.

## Rechtliche Einordnung (keine Rechtsberatung)

- Es werden keine Samples, Loops, Presets, Melodien oder Songs Dritter
  verwendet. Alle Klänge werden berechnet, alle Themen und Akkordfolgen sind in
  diesem Repository notierte eigene Kompositionen.
- Die Titel sind bei keiner Verwertungsgesellschaft angemeldet. Wegen der
  GEMA-Vermutung sollte bei öffentlicher Wiedergabe der Nachweis der
  GEMA-Freiheit vorliegen; dieses Repository mit Notation, Seeds und
  Git-Historie ist dieser Nachweis.
- Skript und gerenderte Audiodateien stehen unter **CC0 1.0** (siehe `LICENSE`).
