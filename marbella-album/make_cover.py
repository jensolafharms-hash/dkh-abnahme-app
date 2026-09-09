#!/usr/bin/env python3
"""
Cover-Artwork für "Sounds of Marbella 2026" (DJ Jensi).

Erzeugt komplett prozedural (Pillow, keine Fremdgrafiken):
  cover/front.png          3000x3000, Digital-/Streaming-Cover
  cover/back.png           3000x3000, Rückseite mit Tracklist & Impressum
  cover/cd-inlay-back.png  CD-Tray-Inlay 150 x 118 mm @ 300 dpi mit zwei Rücken
  cover/cover.pdf          Front + Inlay als Druck-PDF

Impressum-Angaben unten in IMPRESSUM anpassen und Skript erneut ausführen.
Laufzeiten werden direkt aus den Track-Definitionen von generate_album.py
berechnet (identisch mit den gerenderten Dateien).
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import album as al  # noqa: E402

ARTIST = "DJ Jensi"
TITLE_A = "Sounds of"
TITLE_B = "Marbella"
YEAR = "2026"
TAGLINE = "Una noche de verano  ·  Flamenco Chill  ·  Deep House  ·  Trance"

IMPRESSUM = {
    "Künstler": "DJ Jensi",
    "Verantwortlich": "Jens Olaf Harms",
    # Pflichtangaben für den Verkauf einer physischen CD in der EU (Produktsicherheitsverordnung):
    "Anschrift": "[Street No., ZIP City, Country]",
    "Kontakt": "j.harms@comcentra.de",
}

FONT_DIR = "/usr/share/fonts/truetype"
F_SANS_B = f"{FONT_DIR}/dejavu/DejaVuSans-Bold.ttf"
F_SANS = f"{FONT_DIR}/dejavu/DejaVuSans.ttf"
F_SANS_L = f"{FONT_DIR}/liberation/LiberationSans-Regular.ttf"
F_SERIF_I = f"{FONT_DIR}/freefont/FreeSerifItalic.ttf"
F_SERIF = f"{FONT_DIR}/freefont/FreeSerif.ttf"
F_DEJAVU_SERIF_B = f"{FONT_DIR}/dejavu/DejaVuSerif-Bold.ttf"
F_COND = f"{FONT_DIR}/liberation/LiberationSansNarrow-Regular.ttf"
F_COND_B = f"{FONT_DIR}/liberation/LiberationSansNarrow-Bold.ttf"
for _f in (F_SANS_L, F_COND, F_COND_B):
    if not os.path.exists(_f):
        pass


def font(path, size):
    if not os.path.exists(path):
        path = F_SANS
    return ImageFont.truetype(path, int(size))


# --------------------------------------------------------------------------- #
# Grafikbausteine
# --------------------------------------------------------------------------- #
def gradient(w, h, stops):
    """Vertikaler Farbverlauf. stops: [(pos 0..1, (r,g,b)), ...]"""
    ys = np.linspace(0, 1, h)
    pos = np.array([p for p, _ in stops])
    cols = np.array([c for _, c in stops], dtype=float)
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for ch in range(3):
        img[:, :, ch] = np.interp(ys, pos, cols[:, ch])[:, None]
    return Image.fromarray(img, "RGB")


def add_grain(img, amount=6, seed=1):
    rng = np.random.default_rng(seed)
    a = np.asarray(img).astype(np.int16)
    a += rng.integers(-amount, amount + 1, size=a.shape, dtype=np.int16)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def vignette(img, strength=0.35):
    w, h = img.size
    y, x = np.mgrid[0:h, 0:w]
    d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    mask = np.clip(1.0 - strength * np.clip(d - 0.55, 0, None) * 1.6, 0, 1)
    a = np.asarray(img).astype(float) * mask[:, :, None]
    return Image.fromarray(a.astype(np.uint8), "RGB")


def sun(img, cx, cy, r, color=(255, 214, 120), glow=(255, 150, 90), cut_below=None):
    glow_layer = Image.new("RGB", img.size, (0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    gd.ellipse((cx - r * 2.2, cy - r * 2.2, cx + r * 2.2, cy + r * 2.2), fill=glow)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(r * 0.9))
    img = Image.fromarray(np.clip(np.asarray(img).astype(int) + (np.asarray(glow_layer).astype(int) * 0.55), 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    # feine horizontale Schnitte (Retro-Look, dezent)
    for i in range(6):
        yy = cy + r * (0.25 + 0.13 * i)
        th = int(r * 0.012 * (i + 1))
        if yy + th < cy + r:
            d.rectangle((cx - r, yy, cx + r, yy + th), fill=tuple(int(c * 0.85) for c in glow))
    if cut_below is not None:
        d.rectangle((0, cut_below, img.size[0], cy + r + 2), fill=None)
    return img


def sea(img, y0, y1, base=(18, 40, 70), light=(255, 190, 120), cx=None, rng=None):
    w, h = img.size
    d = ImageDraw.Draw(img)
    grad = gradient(w, y1 - y0, [(0, (40, 70, 110)), (1, base)])
    img.paste(grad, (0, y0))
    d = ImageDraw.Draw(img)
    rng = rng or np.random.default_rng(7)
    cx = cx if cx is not None else w // 2
    for i in range(160):
        t = rng.random()
        yy = y0 + int((y1 - y0) * t ** 1.4)
        spread = 60 + 900 * t
        length = int(rng.uniform(20, 140) + 500 * t)
        xx = int(cx + rng.normal(0, spread * 0.5))
        th = max(1, int(1 + 6 * t))
        alpha = (1 - t) * 0.9 + 0.1
        col = tuple(int(b * (1 - alpha) + l * alpha) for b, l in zip(base, light))
        d.rounded_rectangle((xx - length // 2, yy, xx + length // 2, yy + th), radius=th, fill=col)
    return img


def mountain(d, w, y_base, color, peak_x, peak_y, spread):
    """La-Concha-artige Silhouette: markanter Gipfel mit Schultern."""
    pts = [(0, y_base)]
    xs = np.linspace(0, w, 60)
    for x in xs:
        dx = (x - peak_x) / spread
        y = peak_y + (y_base - peak_y) * (1 - math.exp(-dx * dx * 1.8))
        if x > peak_x:  # steilere rechte Flanke, dann Plateau
            y = peak_y + (y_base - peak_y) * (1 - math.exp(-dx * dx * 3.2)) * 0.9 + (y_base - peak_y) * 0.1
        y += 18 * math.sin(x * 0.012) + 10 * math.sin(x * 0.037)
        pts.append((x, min(y, y_base)))
    pts.append((w, y_base))
    d.polygon(pts, fill=color)


def palm(img, x, y_base, height, lean=0.0, scale=1.0, color=(12, 10, 24), seed=3):
    """Palmen-Silhouette: gebogener, segmentierter Stamm; Wedel aus dichten Fiederblättern."""
    rng = np.random.default_rng(seed)
    SS = 2  # Supersampling gegen Treppchen
    W, H = img.size
    layer = Image.new("L", (W * SS, H * SS), 0)
    d = ImageDraw.Draw(layer)
    x, y_base, height = x * SS, y_base * SS, height * SS
    scale *= SS

    # Stamm: leicht gebogen, nach oben schlanker, mit Ringen
    n = 60
    trunk = []
    for i in range(n + 1):
        t = i / n
        tx = x + lean * height * (t ** 1.7) + 6 * scale * math.sin(t * 9.0) * t
        ty = y_base - height * t
        trunk.append((tx, ty))
    for i in range(n):
        t = i / n
        wdt = (17 - 9 * t) * scale
        d.line([trunk[i], trunk[i + 1]], fill=255, width=int(wdt))
        if i % 4 == 0:
            cx, cy = trunk[i]
            d.ellipse((cx - wdt * 0.62, cy - wdt * 0.22, cx + wdt * 0.62, cy + wdt * 0.22), fill=255)
    top = trunk[-1]
    d.ellipse((top[0] - 14 * scale, top[1] - 10 * scale, top[0] + 14 * scale, top[1] + 10 * scale), fill=255)

    # Wedel
    n_fronds = 10
    for k in range(n_fronds):
        ang = -math.pi * 0.06 - math.pi * 0.88 * k / (n_fronds - 1) + rng.uniform(-0.05, 0.05)
        length = height * rng.uniform(0.40, 0.55)
        droop = rng.uniform(0.55, 0.95)
        rib = []
        for j in range(41):
            t = j / 40
            px = top[0] + math.cos(ang) * length * t
            py = top[1] + math.sin(ang) * length * t * 0.45 + droop * length * t * t
            rib.append((px, py))
        d.line(rib, fill=255, width=int(3.2 * scale))
        # Fiederblätter: schmale Dreiecke, nach außen zur Spitze geneigt, beidseitig
        for j in range(5, 40):
            t = j / 40
            px, py = rib[j]
            dx = rib[j + 1][0] - rib[j - 1][0]
            dy = rib[j + 1][1] - rib[j - 1][1]
            ln = math.hypot(dx, dy) + 1e-6
            ux, uy = dx / ln, dy / ln
            leaf_len = length * 0.26 * math.sin(math.pi * min(1.0, 0.12 + t * 0.95)) ** 0.8 * rng.uniform(0.8, 1.0)
            base_w = 4.0 * scale
            for side in (-1, 1):
                nx, ny = -uy * side, ux * side
                # Blattrichtung: Normale + Anteil in Wedelrichtung + Schwerkraft
                lx = nx * 0.75 + ux * 0.55
                ly = ny * 0.75 + uy * 0.55 + 0.55
                ll = math.hypot(lx, ly)
                lx, ly = lx / ll, ly / ll
                tipx, tipy = px + lx * leaf_len, py + ly * leaf_len
                bx, by = -ly * base_w, lx * base_w
                d.polygon([(px + bx, py + by), (px - bx, py - by), (tipx, tipy)], fill=255)

    layer = layer.resize((W, H), Image.LANCZOS)
    solid = Image.new("RGBA", (W, H), color + (255,))
    img.paste(solid, (0, 0), layer)
    return img


PHOTO_FRONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cover", "photo-front.jpg")
PHOTO_BACK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cover", "photo-back.jpg")


PHOTO_ROTATE = 1.0   # Grad gegen den Uhrzeigersinn, damit die Uferlinie waagerecht liegt


def load_photo(path, w, h, darken=0.0, blur=0.0):
    """Foto laden, gerade drehen, auf w x h beschneiden (Bildmitte), optional abdunkeln und weichzeichnen."""
    if not os.path.exists(path):
        return None
    im = Image.open(path).convert("RGB")
    if PHOTO_ROTATE:
        im = im.rotate(PHOTO_ROTATE, resample=Image.BICUBIC, expand=False)
        # Ränder, die durch die Drehung leer werden, wegschneiden
        r = math.radians(abs(PHOTO_ROTATE))
        cut_x = int(math.ceil(im.height * math.sin(r))) + 2
        cut_y = int(math.ceil(im.width * math.sin(r))) + 2
        im = im.crop((cut_x, cut_y, im.width - cut_x, im.height - cut_y))
    scale = max(w / im.width, h / im.height)
    im = im.resize((max(w, int(im.width * scale + 0.5)), max(h, int(im.height * scale + 0.5))), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 2
    im = im.crop((left, top, left + w, top + h))
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    if darken:
        a = np.asarray(im).astype(float) * (1.0 - darken)
        im = Image.fromarray(a.astype(np.uint8), "RGB")
    return im


def overlay_gradient(img, top_alpha=0.55, bottom_alpha=0.65, color=(12, 8, 30)):
    """Dunkler Verlauf oben und unten, damit Text auf dem Foto lesbar bleibt."""
    w, h = img.size
    ys = np.linspace(0, 1, h)
    alpha = np.clip(top_alpha * (1 - ys / 0.42), 0, 1) + np.clip(bottom_alpha * (ys - 0.62) / 0.38, 0, 1)
    a = np.asarray(img).astype(float)
    col = np.array(color, dtype=float)
    a = a * (1 - alpha[:, None, None]) + col * alpha[:, None, None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def text_size(fnt, s):
    l, t, r, b = fnt.getbbox(s)
    return r - l, b - t, l, t


def draw_artist_mirrored_j(img, cx, y, size, fill=(255, 250, 240), shadow=(0, 0, 0)):
    """Schreibt 'DJ Jensi'; nur das J von 'Jensi' ist spiegelverkehrt."""
    fnt = font(F_DEJAVU_SERIF_B, size)
    parts = ["DJ", " ", "J", "ensi"]
    widths = []
    for p in parts:
        w, h, l, t = text_size(fnt, p if p.strip() else "n")
        widths.append(w if p.strip() else int(size * 0.28))
    total = sum(widths) + int(size * 0.02) * (len(parts) - 1)
    x = cx - total // 2
    pad = int(size * 0.5)
    for p, w in zip(parts, widths):
        if not p.strip():
            x += w
            continue
        glyph = Image.new("RGBA", (w + pad * 2, int(size * 1.6)), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        _, _, l, t = text_size(fnt, p)
        gd.text((pad - l, int(size * 0.2) - t), p, font=fnt, fill=fill + (255,))
        if p == "J":
            glyph = ImageOps.mirror(glyph)
        sh = Image.new("RGBA", glyph.size, (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", glyph.size, shadow + (140,)), (0, 0), glyph)
        sh = sh.filter(ImageFilter.GaussianBlur(size * 0.04))
        img.paste(sh, (x - pad + int(size * 0.03), y - int(size * 0.2) + int(size * 0.04)), sh)
        img.paste(glyph, (x - pad, y - int(size * 0.2)), glyph)
        x += w + int(size * 0.02)
    return total


def center_text(d, img_w, y, s, fnt, fill, spacing=0):
    w, h, l, t = text_size(fnt, s)
    if spacing:
        total = sum(text_size(fnt, c)[0] for c in s) + spacing * (len(s) - 1)
        x = (img_w - total) // 2
        for c in s:
            d.text((x - text_size(fnt, c)[2], y - t), c, font=fnt, fill=fill)
            x += text_size(fnt, c)[0] + spacing
        return h
    d.text(((img_w - w) // 2 - l, y - t), s, font=fnt, fill=fill)
    return h


# --------------------------------------------------------------------------- #
# Track-Daten (Laufzeiten exakt wie im Render)
# --------------------------------------------------------------------------- #
def track_data():
    rows = []
    total = 0.0
    # Auf dem Cover nur die Musikrichtungen als Aufzählung, keine Instrumente, keine Tonarten
    style_on_cover = {1: "House, Acid, Chill", 2: "Deep House", 3: "Flamenco Chill, Bulería", 4: "Interlude",
                      5: "Chill, Tribal", 6: "Deep House, Trance", 7: "Ballad, 6/8", 8: "Shuffle House, Dub",
                      9: "Interlude", 10: "Chill, Sunrise"}
    for spec in al.TRACKS:
        dur = al.track_duration(spec)
        total += dur
        rows.append(dict(nr=int(spec["nr"]), title=spec["title"], bpm=style_on_cover.get(int(spec["nr"]), spec["style"]), key="", dur=dur, interlude=False))
    return rows, total


def fmt(sec):
    return f"{int(sec // 60)}:{int(round(sec % 60)):02d}"


# --------------------------------------------------------------------------- #
# Front
# --------------------------------------------------------------------------- #
def make_front(S=3000):
    photo = load_photo(PHOTO_FRONT, S, S)
    if photo is not None:
        img = overlay_gradient(photo, 0.35, 0.78)
        img = vignette(img, 0.25)
        # Name oben in der freien Himmelsfläche zwischen den Palmenkronen
        draw_artist_mirrored_j(img, S // 2, int(S * 0.05), int(S * 0.095))
        d = ImageDraw.Draw(img)
        # Titelblock unten über dem Wasser: Berg und Palmen bleiben frei
        y = int(S * 0.69)
        center_text(d, S, y, TITLE_A.upper(), font(F_SANS_L, S * 0.034), (255, 240, 225), spacing=int(S * 0.012))
        y += int(S * 0.05)
        center_text(d, S, y, TITLE_B.upper(), font(F_SANS_B, S * 0.1), (255, 250, 240), spacing=int(S * 0.010))
        y += int(S * 0.128)
        center_text(d, S, y, YEAR, font(F_SANS_B, S * 0.055), (255, 236, 200), spacing=int(S * 0.02))
        center_text(d, S, int(S * 0.955), TAGLINE.upper(), font(F_SANS, S * 0.017), (215, 205, 225), spacing=int(S * 0.004))
        return img
    img = gradient(S, S, [
        (0.00, (24, 16, 64)),
        (0.22, (92, 30, 110)),
        (0.42, (214, 78, 96)),
        (0.55, (250, 140, 70)),
        (0.62, (255, 196, 110)),
        (1.00, (255, 196, 110)),
    ])
    horizon = int(S * 0.63)
    img = sun(img, S // 2, int(S * 0.585), int(S * 0.16), cut_below=horizon)
    d = ImageDraw.Draw(img)
    # Berge (La Concha) hinter dem Horizont
    mountain(d, S, horizon, (74, 32, 88), peak_x=int(S * 0.30), peak_y=int(S * 0.50), spread=S * 0.16)
    mountain(d, S, horizon, (52, 24, 70), peak_x=int(S * 0.78), peak_y=int(S * 0.56), spread=S * 0.14)
    img = sea(img, horizon, S, cx=S // 2)
    d = ImageDraw.Draw(img)
    # Strand-/Uferband unten
    d.rectangle((0, int(S * 0.90), S, S), fill=(10, 8, 22))
    img = vignette(img, 0.45)
    img = add_grain(img, 5)

    # Typografie
    draw_artist_mirrored_j(img, S // 2, int(S * 0.115), int(S * 0.115))
    d = ImageDraw.Draw(img)
    y = int(S * 0.265)
    center_text(d, S, y, TITLE_A.upper(), font(F_SANS_L, S * 0.036), (255, 240, 225), spacing=int(S * 0.012))
    y += int(S * 0.055)
    center_text(d, S, y, TITLE_B.upper(), font(F_SANS_B, S * 0.105), (255, 250, 240), spacing=int(S * 0.010))
    y += int(S * 0.135)
    center_text(d, S, y, YEAR, font(F_SANS_B, S * 0.060), (92, 30, 78), spacing=int(S * 0.02))
    # Tagline unten
    fnt = font(F_SANS, S * 0.020)
    center_text(d, S, int(S * 0.935), TAGLINE.upper(), fnt, (210, 200, 220), spacing=int(S * 0.004))
    return img


# --------------------------------------------------------------------------- #
# Back (quadratisch, digital)
# --------------------------------------------------------------------------- #
def draw_tracklist(d, x0, x1, y, rows, total, fnt_nr, fnt_t, fnt_m, line_h, fill=(240, 236, 245), dim=(170, 160, 190)):
    for r in rows:
        d.text((x0, y), "–" if r.get("interlude") else f"{r['nr']:02d}", font=fnt_nr, fill=dim)
        tx = x0 + int(line_h * 1.6)
        d.text((tx, y), r["title"], font=fnt_t, fill=fill)
        dur = fmt(r["dur"])
        w, h, l, t = text_size(fnt_t, dur)
        d.text((x1 - w - l, y), dur, font=fnt_t, fill=fill)
        # Punktlinie
        tw = text_size(fnt_t, r["title"])[0]
        dots_x0 = tx + tw + int(line_h * 0.4)
        dots_x1 = x1 - w - int(line_h * 0.4)
        yy = y + int(line_h * 0.62)
        xx = dots_x0
        while xx < dots_x1:
            d.ellipse((xx, yy, xx + max(2, line_h * 0.05), yy + max(2, line_h * 0.05)), fill=dim)
            xx += int(line_h * 0.22)
        d.text((tx, y + int(line_h * 1.12)), r["bpm"] + (f"  ·  {r['key']}" if r.get("key") else ""), font=fnt_m, fill=dim)
        y += int(line_h * (1.6 if r.get("interlude") else 1.9))
    y += int(line_h * 0.2)
    d.line((x0, y, x1, y), fill=dim, width=max(1, int(line_h * 0.03)))
    y += int(line_h * 0.35)
    s = f"Total time  {fmt(total)}"
    w, h, l, t = text_size(fnt_t, s)
    d.text((x1 - w - l, y), s, font=fnt_t, fill=fill)
    return y + int(line_h * 1.4)


def dark_panel(img, box, alpha=215, radius=40):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(box, radius=radius, fill=(8, 6, 24, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.15))
    img.paste(layer, (0, 0), layer)
    return img


def impressum_lines():
    return [
        "All titles written, arranged, produced and mixed by DJ Jensi.",
        "",
        f"Released by {IMPRESSUM['Künstler']}  ·  Manufacturer: {IMPRESSUM['Verantwortlich']}, {IMPRESSUM['Anschrift']}, {IMPRESSUM['Kontakt']}",
        "",
        "℗ & © 2026 DJ Jensi  ·  Sounds of Marbella 2026  ·  All rights reserved.",
        "Unauthorised copying, hiring, lending, public performance and broadcasting of this recording prohibited.",
    ]


def make_back(S=3000):
    photo = load_photo(PHOTO_BACK if os.path.exists(PHOTO_BACK) else PHOTO_FRONT, S, S, darken=0.55, blur=6.0)
    if photo is not None:
        img = overlay_gradient(photo, 0.35, 0.45)
        img = vignette(img, 0.35)
        return _back_text(img, S)
    img = gradient(S, S, [(0, (14, 10, 40)), (0.5, (40, 18, 70)), (1, (12, 20, 48))])
    horizon = int(S * 0.80)
    img = sun(img, int(S * 0.78), int(S * 0.78), int(S * 0.07), color=(255, 200, 130), glow=(200, 90, 90), cut_below=horizon)
    d = ImageDraw.Draw(img)
    mountain(d, S, horizon, (30, 14, 56), peak_x=int(S * 0.25), peak_y=int(S * 0.70), spread=S * 0.18)
    img = sea(img, horizon, S, base=(10, 16, 40), light=(255, 170, 120), cx=int(S * 0.78), rng=np.random.default_rng(11))
    img = vignette(img, 0.4)
    img = add_grain(img, 4)
    return _back_text(img, S)


def _back_text(img, S):
    d = ImageDraw.Draw(img)
    m = int(S * 0.10)
    draw_artist_mirrored_j(img, S // 2, int(S * 0.075), int(S * 0.062))
    d = ImageDraw.Draw(img)
    center_text(d, S, int(S * 0.165), f"{TITLE_A} {TITLE_B} {YEAR}".upper(), font(F_SANS_B, S * 0.030), (255, 240, 225), spacing=int(S * 0.006))
    d.line((m, int(S * 0.215), S - m, int(S * 0.215)), fill=(150, 130, 180), width=3)

    rows, total = track_data()
    lh = int(S * 0.0245)
    y = draw_tracklist(d, m, S - m, int(S * 0.235), rows, total,
                       font(F_SANS, lh * 0.75), font(F_SANS, lh * 0.95), font(F_SANS, lh * 0.5), lh)

    fnt = font(F_SANS, S * 0.0135)
    y = max(y, int(S * 0.755))
    lines = impressum_lines()
    img = dark_panel(img, (m, y - int(S * 0.02), S - m, y + int(S * 0.021) * len(lines) + int(S * 0.012)))
    d = ImageDraw.Draw(img)
    for line in lines:
        if line:
            center_text(d, S, y, line, fnt, (200, 190, 215))
        y += int(S * 0.021)
    return img


# --------------------------------------------------------------------------- #
# CD-Inlay Rückseite (150 x 118 mm, 300 dpi, mit zwei Rücken à 6,5 mm)
# --------------------------------------------------------------------------- #
def make_inlay(dpi=300):
    mm = dpi / 25.4
    W, H = int(150 * mm), int(118 * mm)
    spine = int(6.5 * mm)
    photo = load_photo(PHOTO_BACK if os.path.exists(PHOTO_BACK) else PHOTO_FRONT, W, H, darken=0.55, blur=5.0)
    if photo is not None:
        img = overlay_gradient(photo, 0.35, 0.4)
    else:
        img = gradient(W, H, [(0, (14, 10, 40)), (0.55, (44, 20, 76)), (1, (12, 20, 48))])
        horizon = int(H * 0.82)
        img = sun(img, int(W * 0.75), int(H * 0.80), int(H * 0.07), color=(255, 200, 130), glow=(200, 90, 90))
        d = ImageDraw.Draw(img)
        mountain(d, W, horizon, (30, 14, 56), peak_x=int(W * 0.30), peak_y=int(H * 0.72), spread=W * 0.14)
        img = sea(img, horizon, H, base=(10, 16, 40), light=(255, 170, 120), cx=int(W * 0.75), rng=np.random.default_rng(21))
        img = add_grain(img, 4)
    d = ImageDraw.Draw(img)
    # Rücken
    for sx in (0, W - spine):
        d.rectangle((sx, 0, sx + spine, H), fill=(18, 12, 44))
        sp = Image.new("RGBA", (H, spine), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sp)
        fnt = font(F_SANS_B, spine * 0.42)
        s = f"DJ JENSI     ·     SOUNDS OF MARBELLA {YEAR}"
        w, h, l, t = text_size(fnt, s)
        sd.text(((H - w) // 2 - l, (spine - h) // 2 - t), s, font=fnt, fill=(240, 230, 250, 255))
        sp = sp.rotate(90 if sx == 0 else -90, expand=True)
        img.paste(sp, (sx, 0), sp)
    d = ImageDraw.Draw(img)
    x0, x1 = spine + int(6 * mm), W - spine - int(6 * mm)
    draw_artist_mirrored_j(img, W // 2, int(4 * mm), int(9 * mm))
    d = ImageDraw.Draw(img)
    center_text(d, W, int(15.5 * mm), f"{TITLE_A} {TITLE_B} {YEAR}".upper(), font(F_SANS_B, 3.4 * mm), (255, 240, 225), spacing=int(0.6 * mm))
    d.line((x0, int(20.5 * mm), x1, int(20.5 * mm)), fill=(150, 130, 180), width=2)
    rows, total = track_data()
    lh = int(2.9 * mm)
    y = draw_tracklist(d, x0, x1, int(22.0 * mm), rows, total,
                       font(F_SANS, lh * 0.7), font(F_SANS, lh * 0.85), font(F_SANS, lh * 0.48), lh)
    fnt = font(F_SANS, 1.5 * mm)
    y = max(y, int(93 * mm))
    lines = impressum_lines()
    img = dark_panel(img, (x0, y - int(2 * mm), x1, y + int(2.4 * mm) * len(lines) + int(1 * mm)), radius=int(2 * mm))
    d = ImageDraw.Draw(img)
    for line in lines:
        if line:
            center_text(d, W, y, line, fnt, (205, 195, 220))
        y += int(2.4 * mm)
    return img


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cover")
    os.makedirs(out, exist_ok=True)
    front = make_front()
    front.save(os.path.join(out, "front.png"), dpi=(300, 300))
    front.resize((1400, 1400), Image.LANCZOS).save(os.path.join(out, "front-1400.jpg"), quality=92)
    back = make_back()
    back.save(os.path.join(out, "back.png"), dpi=(300, 300))
    back.resize((1400, 1400), Image.LANCZOS).save(os.path.join(out, "back-1400.jpg"), quality=92)
    inlay = make_inlay()
    inlay.save(os.path.join(out, "cd-inlay-back.png"), dpi=(300, 300))
    # Druck-PDF: Front als 120x120 mm Booklet-Seite + Inlay
    mm = 300 / 25.4
    front_print = front.resize((int(120 * mm), int(120 * mm)), Image.LANCZOS)
    front_print.save(os.path.join(out, "cover.pdf"), "PDF", resolution=300.0, save_all=True, append_images=[inlay])
    print("Cover geschrieben nach", out)


if __name__ == "__main__":
    main()
