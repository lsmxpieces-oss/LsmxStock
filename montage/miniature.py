#!/usr/bin/env python3
"""Miniature TikTok LSMX (1080x1920).

python3 montage/miniature.py FOND.jpg -o mini.jpg --ligne1 "TOUT LE STOCK" \
    --ligne2 "D'UN CONCESSIONNAIRE KTM" --chiffre "2000 PIÈCES" [--zoom ZOOM.jpg]
"""
import argparse, math
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

W, H = 1080, 1920
RED, YELLOW = (232, 0, 13), (255, 214, 0)
BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def cover(im, w, h):
    return ImageOps.fit(im.convert("RGB"), (w, h), Image.LANCZOS)


def grade(im):
    im = ImageEnhance.Color(im).enhance(1.45)
    im = ImageEnhance.Contrast(im).enhance(1.18)
    im = im.filter(ImageFilter.UnsharpMask(radius=3, percent=90, threshold=2))
    # vignette
    v = Image.new("L", im.size, 0); d = ImageDraw.Draw(v)
    d.ellipse([-W * 0.35, -H * 0.2, W * 1.35, H * 1.2], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(220))
    return Image.composite(im, Image.new("RGB", im.size, (0, 0, 0)), v)


def fit_font(text, max_w, size):
    while size > 30:
        f = ImageFont.truetype(BLACK, size)
        if f.getbbox(text)[2] <= max_w:
            return f
        size -= 4
    return ImageFont.truetype(BLACK, size)


def text_block(base, text, y, fill, bg=None, size=130, max_w=960, stroke=10, rot=0):
    f = fit_font(text, max_w - (60 if bg else 0), size)
    l, t, r, b = f.getbbox(text)
    tw, th = r - l, b - t
    pad_x, pad_y = (34, 22) if bg else (0, 0)
    layer = Image.new("RGBA", (tw + 2 * pad_x + 40, th + 2 * pad_y + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if bg:
        d.rounded_rectangle([20, 20, 20 + tw + 2 * pad_x, 20 + th + 2 * pad_y], radius=18, fill=bg)
    d.text((20 + pad_x - l, 20 + pad_y - t), text, font=f, fill=fill,
           stroke_width=0 if bg else stroke, stroke_fill="black")
    if rot:
        layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    # ombre portée
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.putalpha(layer.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda a: int(a * 0.7)))
    x = (W - layer.width) // 2
    base.alpha_composite(sh, (x + 8, y + 12)); base.alpha_composite(layer, (x, y))
    return y + layer.height


def circle_inset(base, im, cx, cy, r):
    im = grade_small(cover(im, 2 * r, 2 * r))
    m = Image.new("L", (2 * r, 2 * r), 0); ImageDraw.Draw(m).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
    ring = Image.new("RGBA", (2 * r + 40, 2 * r + 40), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([0, 0, 2 * r + 39, 2 * r + 39], fill=(255, 255, 255, 255))
    ImageDraw.Draw(ring).ellipse([8, 8, 2 * r + 31, 2 * r + 31], fill=RED + (255,))
    sh = Image.new("RGBA", ring.size, (0, 0, 0, 0)); sh.putalpha(ring.getchannel("A").filter(ImageFilter.GaussianBlur(18)))
    base.alpha_composite(sh, (cx - r - 20 + 10, cy - r - 20 + 14))
    base.alpha_composite(ring, (cx - r - 20, cy - r - 20))
    base.paste(im, (cx - r, cy - r), m)


def grade_small(im):
    return ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.5)).enhance(1.15)


def arrow(base, x0, y0, x1, y1, color=YELLOW, w=34):
    d = ImageDraw.Draw(base)
    ang = math.atan2(y1 - y0, x1 - x0); hl = 95
    bx, by = x1 - hl * math.cos(ang), y1 - hl * math.sin(ang)
    head = [(x1, y1), (bx + 62 * math.sin(ang), by - 62 * math.cos(ang)),
            (bx - 62 * math.sin(ang), by + 62 * math.cos(ang))]
    for c, extra in (("black", 12), (color, 0)):
        d.line([(x0, y0), (bx, by)], fill=c, width=w + extra)
        hh = [(px + (8 if extra else 0) * math.cos(ang), py + (8 if extra else 0) * math.sin(ang)) for px, py in head]
        d.polygon(hh if not extra else head, fill=c, outline="black" if extra else None)


def emoji(base, ch, x, y, size=190, rot=0):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
    im = im.crop(im.getbbox()).resize((size, size), Image.LANCZOS).rotate(rot, expand=True, resample=Image.BICUBIC)
    base.alpha_composite(im, (x, y))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("fond"); p.add_argument("-o", "--out", required=True)
    p.add_argument("--ligne1", required=True); p.add_argument("--ligne2", default="")
    p.add_argument("--chiffre", default=""); p.add_argument("--zoom")
    p.add_argument("--emoji", default="🤯")
    a = p.parse_args()

    base = grade(cover(Image.open(a.fond), W, H)).convert("RGBA")
    # dégradé sombre en haut pour la lisibilité du texte
    g = Image.new("L", (1, H)); g.putdata([int(max(0, 215 * (1 - y / 1050))) for y in range(H)])
    base.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [g.resize((W, H))]))

    # zone sûre TikTok : texte entre y=230 et y=1150, rien sous 1500 ni à droite (icônes)
    y = text_block(base, a.ligne1.upper(), 265, "white", size=150, stroke=12)
    if a.ligne2:
        y = text_block(base, a.ligne2.upper(), y - 10, "white", bg=RED + (255,), size=92, rot=-2)
    if a.chiffre:
        y = text_block(base, a.chiffre.upper(), y + 5, YELLOW, size=170, stroke=14)
    if a.zoom:
        circle_inset(base, Image.open(a.zoom), 300, 1240, 210)
        arrow(base, 560, 1310, 760, 1150)
    if a.emoji:
        emoji(base, a.emoji, 830, 50, 175, rot=-12)
    # logo LSMX
    f = ImageFont.truetype(BLACK, 56); d = ImageDraw.Draw(base)
    l, t, r, b = f.getbbox("LSMX"); bx, by = 60, 110
    d.rounded_rectangle([bx, by, bx + r - l + 44, by + b - t + 30], radius=12, fill=RED)
    d.text((bx + 22 - l, by + 15 - t), "LSMX", font=f, fill="white")
    base.convert("RGB").save(a.out, quality=95)
    print("OK ->", a.out)


if __name__ == "__main__":
    main()
