#!/usr/bin/env python3
"""
Das ganze Album als EINE Datei: HTML mit eingebettetem Cover (Front und
Rückseite) und allen Titeln. Öffnet sich per Doppelklick in jedem Browser,
auch offline; jeder Titel ist einzeln anwählbar.

    python3 make_album_file.py                  # volle Qualität (MP3 192 kbit/s aus out/)
    python3 make_album_file.py --kbps 96        # kleinere Fassung, neu kodiert
"""
import argparse
import base64
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

PAGE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DJ Jensi – Sounds of Marbella 2026</title>
<style>
:root{{--bg:#140f2e;--bg2:#1f1747;--bg3:#2c2160;--text:#f3e9dc;--muted:#a99dc9;--accent:#e8607a;--gold:#f2c57c;--line:rgba(243,233,220,.14)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:"Segoe UI",system-ui,-apple-system,sans-serif;font-size:15px;line-height:1.5}}
.wrap{{max-width:1080px;margin:0 auto;padding:28px 20px 64px;display:grid;grid-template-columns:320px 1fr;gap:40px;align-items:start}}
@media (max-width:760px){{.wrap{{grid-template-columns:1fr;gap:24px;padding:16px 14px 56px}}.side{{position:static}}}}
.side{{position:sticky;top:16px;display:flex;flex-direction:column;gap:14px}}
.cover{{width:100%;aspect-ratio:1;border-radius:6px;box-shadow:0 18px 40px rgba(0,0,0,.5);display:block;cursor:pointer}}
.flip{{font-size:12px;color:var(--muted);text-align:center;margin:-6px 0 0}}
.artist{{font-family:Georgia,"Times New Roman",serif;font-weight:700;font-size:32px;line-height:1;margin:0}}
.artist .j{{display:inline-block;transform:scaleX(-1)}}
.album{{margin:2px 0 0;font-size:13px;text-transform:uppercase;letter-spacing:.14em;color:var(--muted)}}
.now{{border-top:1px solid var(--line);padding-top:12px;display:flex;flex-direction:column;gap:10px}}
.now .label{{font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:var(--muted)}}
.now .title{{font-family:Georgia,serif;font-size:20px;line-height:1.2;min-height:1.2em}}
.times{{display:flex;justify-content:space-between;font-variant-numeric:tabular-nums;color:var(--muted);font-size:13px}}
input[type=range]{{width:100%;accent-color:var(--accent);margin:0}}
.transport{{display:flex;gap:10px;align-items:center}}
button{{font:inherit;color:var(--text);background:var(--bg3);border:1px solid var(--line);border-radius:999px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center}}
.transport button{{width:44px;height:44px}}
.transport .big{{width:56px;height:56px;background:var(--accent);border-color:transparent;color:#fff}}
.list{{display:flex;flex-direction:column;border-top:1px solid var(--line)}}
.row{{display:grid;grid-template-columns:44px 28px 1fr auto;gap:14px;align-items:center;padding:13px 8px;border-bottom:1px solid var(--line);position:relative;cursor:pointer}}
.row:hover,.row.active{{background:var(--bg2)}}
.row .play{{width:40px;height:40px}}
.row.active .play{{background:var(--accent);border-color:transparent;color:#fff}}
.row .nr{{font-variant-numeric:tabular-nums;color:var(--muted);font-size:13px}}
.row .t{{font-weight:600;font-size:16px}}
.row .m{{color:var(--muted);font-size:12.5px;margin-top:2px}}
.row .d{{font-variant-numeric:tabular-nums;color:var(--muted);font-size:13px}}
.row .bar{{position:absolute;left:0;right:0;bottom:-1px;height:2px;background:var(--gold);transform-origin:left;transform:scaleX(0)}}
.head{{display:flex;justify-content:space-between;align-items:baseline;margin:0 0 10px}}
.head h2{{font-family:Georgia,serif;font-weight:600;font-size:22px;margin:0}}
.head span{{color:var(--muted);font-size:13px}}
.legal{{margin-top:28px;color:var(--muted);font-size:12px;line-height:1.6}}
svg{{width:18px;height:18px;fill:currentColor}}
</style></head><body>
<div class="wrap">
  <aside class="side">
    <img class="cover" id="cover" src="{front}" data-front="{front}" data-back="{back}" alt="Cover" title="Klicken: Vorder-/Rückseite">
    <p class="flip">Cover anklicken: Vorderseite / Rückseite</p>
    <div><h1 class="artist">DJ <span class="j">J</span>ensi</h1><p class="album">Sounds of Marbella 2026</p></div>
    <div class="now">
      <div class="label">Now playing</div>
      <div class="title" id="nowTitle">Titel auswählen</div>
      <input type="range" id="seek" min="0" max="1000" value="0" aria-label="Position">
      <div class="times"><span id="cur">0:00</span><span id="tot">0:00</span></div>
      <div class="transport">
        <button id="prev" aria-label="Vorheriger Titel"><svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6 8.5 6V6z"/></svg></button>
        <button id="toggle" class="big" aria-label="Abspielen"><svg id="icoPlay" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg><svg id="icoPause" viewBox="0 0 24 24" hidden><path d="M6 5h4v14H6zm8 0h4v14h-4z"/></svg></button>
        <button id="next" aria-label="Nächster Titel"><svg viewBox="0 0 24 24"><path d="M16 6h2v12h-2zM6 18l8.5-6L6 6z"/></svg></button>
      </div>
    </div>
  </aside>
  <main>
    <div class="head"><h2>Titel</h2><span>{total}</span></div>
    <div class="list" id="list"></div>
    <p class="legal">℗ &amp; © 2026 DJ Jensi · Sounds of Marbella 2026 · All rights reserved. Diese Datei enthält das komplette Album ({kbps} kbit/s) und funktioniert ohne Internet.</p>
  </main>
</div>
<audio id="audio" preload="none"></audio>
<script>
const TRACKS = {tracks};
const audio = document.getElementById('audio'), list = document.getElementById('list');
const nowTitle = document.getElementById('nowTitle'), seek = document.getElementById('seek');
const cur = document.getElementById('cur'), tot = document.getElementById('tot');
const icoPlay = document.getElementById('icoPlay'), icoPause = document.getElementById('icoPause');
let idx = -1, seeking = false;
const fmt = s => isFinite(s) ? Math.floor(s/60) + ':' + String(Math.floor(s%60)).padStart(2,'0') : '0:00';
TRACKS.forEach((t, i) => {{
  const row = document.createElement('div'); row.className = 'row';
  row.innerHTML = `<button class="play" aria-label="Abspielen: ${{t.title}}"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></button>
    <span class="nr">${{String(t.nr).padStart(2,'0')}}</span><div><div class="t">${{t.title}}</div><div class="m">${{t.meta}}</div></div>
    <span class="d">${{fmt(t.dur)}}</span><div class="bar"></div>`;
  row.addEventListener('click', () => (i === idx ? toggle() : load(i, true)));
  list.appendChild(row);
}});
function load(i, autoplay) {{
  idx = i; const t = TRACKS[i];
  audio.src = t.src; nowTitle.textContent = String(t.nr).padStart(2,'0') + ' · ' + t.title; tot.textContent = fmt(t.dur);
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
  if (!audio.duration) return; const p = audio.currentTime / audio.duration;
  if (!seeking) seek.value = Math.round(p * 1000); cur.textContent = fmt(audio.currentTime);
  const row = list.children[idx]; if (row) row.querySelector('.bar').style.transform = `scaleX(${{p}})`;
}});
seek.addEventListener('input', () => {{ seeking = true; cur.textContent = fmt(seek.value / 1000 * (audio.duration || 0)); }});
seek.addEventListener('change', () => {{ if (audio.duration) audio.currentTime = seek.value / 1000 * audio.duration; seeking = false; }});
document.addEventListener('keydown', e => {{ if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'BUTTON') {{ e.preventDefault(); toggle(); }} }});
const cover = document.getElementById('cover');
cover.addEventListener('click', () => {{ cover.src = cover.src === cover.dataset.front ? cover.dataset.back : cover.dataset.front; }});
</script></body></html>
"""


def b64(path):
    return base64.b64encode(open(path, "rb").read()).decode()


def reencode(path, kbps):
    import lameenc
    import miniaudio
    d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=2, sample_rate=44100)
    enc = lameenc.Encoder()
    enc.set_bit_rate(kbps)
    enc.set_in_sample_rate(44100)
    enc.set_channels(2)
    enc.set_quality(2)
    return enc.encode(bytes(d.samples)) + enc.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kbps", type=int, default=0, help="0 = Originaldateien einbetten (192 kbit/s), sonst neu kodieren")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "Sounds-of-Marbella-2026.html"))
    args = ap.parse_args()
    tl = json.load(open(os.path.join(HERE, "out", "tracklist.json"), encoding="utf-8"))
    front = "data:image/jpeg;base64," + b64(os.path.join(HERE, "cover", "front-1400.jpg"))
    back = "data:image/jpeg;base64," + b64(os.path.join(HERE, "cover", "back-1400.jpg"))
    items, total = [], 0.0
    for i, tr in enumerate(tl["tracks"], 1):
        path = os.path.join(HERE, "out", tr["file"])
        data = reencode(path, args.kbps) if args.kbps else open(path, "rb").read()
        items.append(dict(nr=i, title=html.escape(tr["title"]), meta=html.escape(tr["style"]), dur=tr["duration_s"],
                          src="data:audio/mpeg;base64," + base64.b64encode(data).decode()))
        total += tr["duration_s"]
    page = PAGE.format(front=front, back=back, tracks=json.dumps(items, ensure_ascii=False),
                       total=f"{len(items)} Titel · {int(total // 60)}:{int(total % 60):02d} min", kbps=args.kbps or 192)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(args.out, f"{os.path.getsize(args.out) / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
