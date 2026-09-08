#!/usr/bin/env python3
"""
Erzeugt Web-Player-Seiten (HTML mit eingebettetem Audio), damit das Album ohne
Zusatzprogramm im Browser läuft. Die Titel werden dafür auf 96 kbit/s
neu kodiert; die MP3s in out/ bleiben in voller Qualität.

    python3 make_player.py --out /pfad     # schreibt player-1.html, player-2.html
"""
import argparse
import base64
import html
import json
import os

import lameenc
import miniaudio

HERE = os.path.dirname(os.path.abspath(__file__))
PER_PAGE = 4
BITRATE = 96


def reencode(path, kbps=BITRATE):
    d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=2, sample_rate=44100)
    enc = lameenc.Encoder()
    enc.set_bit_rate(kbps)
    enc.set_in_sample_rate(44100)
    enc.set_channels(2)
    enc.set_quality(2)
    return enc.encode(bytes(d.samples)) + enc.flush(), d.num_frames / 44100.0


PAGE = """<title>{title}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,800&family=Work+Sans:wght@400;500;600&display=swap">
<style>
:root{{--bg:#1b1340;--bg2:#241a4e;--bg3:#2f2360;--text:#f3e9dc;--muted:#a99dc9;--accent:#e8607a;--gold:#f2c57c;--line:rgba(243,233,220,.14);--shadow:rgba(0,0,0,.45)}}
@media (prefers-color-scheme: light){{:root:not([data-theme="dark"]){{--bg:#f7efe3;--bg2:#fffaf2;--bg3:#f0e4d0;--text:#221a4a;--muted:#6e6389;--accent:#d1425f;--gold:#a8761f;--line:rgba(34,26,74,.14);--shadow:rgba(34,26,74,.18)}}}}
:root[data-theme="light"]{{--bg:#f7efe3;--bg2:#fffaf2;--bg3:#f0e4d0;--text:#221a4a;--muted:#6e6389;--accent:#d1425f;--gold:#a8761f;--line:rgba(34,26,74,.14);--shadow:rgba(34,26,74,.18)}}
:root[data-theme="dark"]{{--bg:#1b1340;--bg2:#241a4e;--bg3:#2f2360;--text:#f3e9dc;--muted:#a99dc9;--accent:#e8607a;--gold:#f2c57c;--line:rgba(243,233,220,.14);--shadow:rgba(0,0,0,.45)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:"Work Sans",system-ui,sans-serif;font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1080px;margin:0 auto;padding:32px 20px 64px;display:grid;grid-template-columns:300px 1fr;gap:40px;align-items:start}}
@media (max-width:760px){{.wrap{{grid-template-columns:1fr;gap:24px;padding:20px 14px 56px}}.side{{position:static}}}}
.side{{position:sticky;top:20px;display:flex;flex-direction:column;gap:16px}}
.cover{{width:100%;aspect-ratio:1;border-radius:6px;box-shadow:0 18px 40px var(--shadow);display:block}}
.artist{{font-family:Fraunces,Georgia,serif;font-weight:800;font-size:34px;line-height:1;margin:0;letter-spacing:-.01em}}
.artist .j{{display:inline-block;transform:scaleX(-1)}}
.album{{margin:2px 0 0;font-size:13px;text-transform:uppercase;letter-spacing:.14em;color:var(--muted)}}
.now{{border-top:1px solid var(--line);padding-top:14px;display:flex;flex-direction:column;gap:10px}}
.now .label{{font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:var(--muted)}}
.now .title{{font-family:Fraunces,Georgia,serif;font-weight:600;font-size:20px;line-height:1.2;text-wrap:balance;min-height:1.2em}}
.times{{display:flex;justify-content:space-between;font-variant-numeric:tabular-nums;color:var(--muted);font-size:13px}}
input[type=range]{{width:100%;accent-color:var(--accent);margin:0}}
.transport{{display:flex;gap:10px;align-items:center}}
button{{font:inherit;color:var(--text);background:var(--bg3);border:1px solid var(--line);border-radius:999px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center}}
button:focus-visible{{outline:2px solid var(--gold);outline-offset:2px}}
.transport button{{width:44px;height:44px}}
.transport .big{{width:56px;height:56px;background:var(--accent);border-color:transparent;color:#fff}}
.hint{{font-size:12.5px;color:var(--muted);margin:0}}
.hint a{{color:var(--gold)}}
.list{{display:flex;flex-direction:column;gap:0;border-top:1px solid var(--line)}}
.row{{display:grid;grid-template-columns:44px 28px 1fr auto;gap:14px;align-items:center;padding:14px 8px;border-bottom:1px solid var(--line);position:relative;cursor:pointer}}
.row:hover{{background:var(--bg2)}}
.row.active{{background:var(--bg2)}}
.row .play{{width:40px;height:40px}}
.row.active .play{{background:var(--accent);border-color:transparent;color:#fff}}
.row .nr{{font-variant-numeric:tabular-nums;color:var(--muted);font-size:13px}}
.row .t{{font-weight:600;font-size:16px}}
.row .m{{color:var(--muted);font-size:12.5px;margin-top:2px}}
.row .d{{font-variant-numeric:tabular-nums;color:var(--muted);font-size:13px}}
.row .bar{{position:absolute;left:0;right:0;bottom:-1px;height:2px;background:var(--gold);transform-origin:left;transform:scaleX(0)}}
.head{{display:flex;justify-content:space-between;align-items:baseline;margin:0 0 10px}}
.head h2{{font-family:Fraunces,Georgia,serif;font-weight:600;font-size:22px;margin:0}}
.head span{{color:var(--muted);font-size:13px}}
svg{{width:18px;height:18px;fill:currentColor}}
@media (prefers-reduced-motion:no-preference){{.row .bar{{transition:transform .25s linear}}}}
</style>
<div class="wrap">
  <aside class="side">
    <img class="cover" src="{cover}" alt="Cover: Sonnenuntergang über dem Meer bei Marbella">
    <div>
      <h1 class="artist">DJ <span class="j">J</span>ensi</h1>
      <p class="album">Sounds of Marbella 2026</p>
    </div>
    <div class="now">
      <div class="label">Läuft gerade</div>
      <div class="title" id="nowTitle">Titel auswählen</div>
      <input type="range" id="seek" min="0" max="1000" value="0" aria-label="Position">
      <div class="times"><span id="cur">0:00</span><span id="tot">0:00</span></div>
      <div class="transport">
        <button id="prev" aria-label="Vorheriger Titel"><svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6 8.5 6V6z"/></svg></button>
        <button id="toggle" class="big" aria-label="Abspielen"><svg id="icoPlay" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg><svg id="icoPause" viewBox="0 0 24 24" hidden><path d="M6 5h4v14H6zm8 0h4v14h-4z"/></svg></button>
        <button id="next" aria-label="Nächster Titel"><svg viewBox="0 0 24 24"><path d="M16 6h2v12h-2zM6 18l8.5-6L6 6z"/></svg></button>
      </div>
      <p class="hint">{hint}</p>
    </div>
  </aside>
  <main>
    <div class="head"><h2>{heading}</h2><span>{total}</span></div>
    <div class="list" id="list"></div>
  </main>
</div>
<audio id="audio" preload="none"></audio>
<script>
const TRACKS = {tracks};
const audio = document.getElementById('audio');
const list = document.getElementById('list');
const nowTitle = document.getElementById('nowTitle');
const seek = document.getElementById('seek');
const cur = document.getElementById('cur'), tot = document.getElementById('tot');
const icoPlay = document.getElementById('icoPlay'), icoPause = document.getElementById('icoPause');
let idx = -1, seeking = false;
const fmt = s => isFinite(s) ? Math.floor(s/60) + ':' + String(Math.floor(s%60)).padStart(2,'0') : '0:00';
TRACKS.forEach((t, i) => {{
  const row = document.createElement('div'); row.className = 'row'; row.dataset.i = i;
  row.innerHTML = `<button class="play" aria-label="Abspielen: ${{t.title}}"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></button>
    <span class="nr">${{String(t.nr).padStart(2,'0')}}</span>
    <div><div class="t">${{t.title}}</div><div class="m">${{t.meta}}</div></div>
    <span class="d">${{fmt(t.dur)}}</span><div class="bar"></div>`;
  row.addEventListener('click', () => (i === idx ? toggle() : load(i, true)));
  list.appendChild(row);
}});
function load(i, autoplay) {{
  idx = i; const t = TRACKS[i];
  audio.src = t.src; nowTitle.textContent = t.title; tot.textContent = fmt(t.dur);
  document.querySelectorAll('.row').forEach((r, k) => {{ r.classList.toggle('active', k === i); if (k !== i) r.querySelector('.bar').style.transform = 'scaleX(0)'; }});
  if (autoplay) audio.play();
}}
function toggle() {{ if (idx < 0) return load(0, true); audio.paused ? audio.play() : audio.pause(); }}
document.getElementById('toggle').addEventListener('click', toggle);
document.getElementById('next').addEventListener('click', () => load((idx + 1) % TRACKS.length, true));
document.getElementById('prev').addEventListener('click', () => load((idx - 1 + TRACKS.length) % TRACKS.length, true));
audio.addEventListener('play', () => {{ icoPlay.hidden = true; icoPause.hidden = false; }});
audio.addEventListener('pause', () => {{ icoPlay.hidden = false; icoPause.hidden = true; }});
audio.addEventListener('ended', () => {{ if (idx + 1 < TRACKS.length) load(idx + 1, true); }});
audio.addEventListener('timeupdate', () => {{
  if (!audio.duration) return;
  const p = audio.currentTime / audio.duration;
  if (!seeking) seek.value = Math.round(p * 1000);
  cur.textContent = fmt(audio.currentTime);
  const row = list.children[idx]; if (row) row.querySelector('.bar').style.transform = `scaleX(${{p}})`;
}});
seek.addEventListener('input', () => {{ seeking = true; cur.textContent = fmt(seek.value / 1000 * (audio.duration || 0)); }});
seek.addEventListener('change', () => {{ if (audio.duration) audio.currentTime = seek.value / 1000 * audio.duration; seeking = false; }});
document.addEventListener('keydown', e => {{ if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'BUTTON') {{ e.preventDefault(); toggle(); }} }});
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=HERE)
    args = ap.parse_args()
    with open(os.path.join(HERE, "out", "tracklist.json"), encoding="utf-8") as fh:
        tl = json.load(fh)
    cover = "data:image/jpeg;base64," + base64.b64encode(open(os.path.join(HERE, "cover", "front-1400.jpg"), "rb").read()).decode()
    tracks = tl["tracks"]
    pages = [tracks[i:i + PER_PAGE] for i in range(0, len(tracks), PER_PAGE)]
    for pi, group in enumerate(pages, 1):
        items = []
        for tr in group:
            data, dur = reencode(os.path.join(HERE, "out", tr["file"]))
            items.append(dict(nr=tr["nr"], title=html.escape(tr["title"]), meta=f"{tr['bpm']} BPM · {html.escape(tr['key'])}",
                              dur=round(dur, 1), src="data:audio/mpeg;base64," + base64.b64encode(data).decode()))
            print(f"  {tr['file']}: {len(data)//1024} KB @ {BITRATE} kbit/s", flush=True)
        first, last = group[0]["nr"], group[-1]["nr"]
        total = sum(it["dur"] for it in items)
        page = PAGE.format(
            title=f"Sounds of Marbella 2026 · Titel {first}–{last}",
            cover=cover,
            hint=(f"Diese Seite enthält die Titel {first} bis {last} von {len(tracks)} in Vorschau-Qualität ({BITRATE} kbit/s). "
                  "Die MP3s in voller Qualität liegen im Repository unter marbella-album/out."),
            heading=f"Titel {first}–{last}",
            total=f"{int(total // 60)}:{int(total % 60):02d} min",
            tracks=json.dumps(items, ensure_ascii=False),
        )
        path = os.path.join(args.out, f"sounds-of-marbella-player-{pi}.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(page)
        print(path, os.path.getsize(path) // 1024 // 1024, "MB")


if __name__ == "__main__":
    main()
