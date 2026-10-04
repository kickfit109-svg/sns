"""等高線の背景の上に、緑の筆（右肩下がり・本数少なめ・黄緑のアクセント）を重ねる。"""
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from brush_strokes import draw_stroke, splatter  # noqa: E402

DEEP = (2, 58, 32); MAIN = (0, 110, 52); BRAND = (0, 150, 62); LIGHT = (70, 190, 90); LIME = (150, 205, 60); PALE = (190, 235, 170)


def compose(base_path, out_path, angle, strokes, splats, seed, strength=0.88):
    base = Image.open(base_path).convert("RGB")
    W, H = base.size
    rng = np.random.default_rng(seed)
    L = int(np.hypot(W, H)) + 200
    canvas = np.zeros((L, L, 4), float)
    for s in strokes:
        kw = {k: (v * L if k in ("yc", "xs", "xe") else v) for k, v in s.items()}
        draw_stroke(canvas, rng, **kw)
    for sp in splats:
        splatter(canvas, rng, sp["cx"] * L, sp["cy"] * L, sp["sx"], sp["sy"], sp["n"], sp["color"], sp.get("rmax", 6))
    img = Image.fromarray(np.clip(canvas * [1, 1, 1, 255], 0, 255).astype(np.uint8), "RGBA")
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False)
    l, t = (L - W) // 2, (L - H) // 2
    img = img.crop((l, t, l + W, t + H))
    a = np.array(img).astype(float)
    alpha = (a[..., 3:] / 255.0) * strength
    out = np.array(base).astype(float) * (1 - alpha) + a[..., :3] * alpha
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(out_path)
    print("saved", out_path)


LAND = [
    dict(yc=0.40, hw=150, xs=0.10, xe=0.80, color=DEEP, light=MAIN, dry_end=0.30, base=0.05),
    dict(yc=0.50, hw=185, xs=0.05, xe=0.93, color=MAIN, light=BRAND, dry_end=0.34),
    dict(yc=0.60, hw=150, xs=0.12, xe=0.88, color=DEEP, light=BRAND, dry_end=0.30),
    dict(yc=0.46, hw=24, xs=0.30, xe=0.82, color=LIME, light=PALE, dry_end=0.60, wob=10, base=0.34, speck=0.09),
    dict(yc=0.57, hw=18, xs=0.20, xe=0.74, color=LIGHT, light=PALE, dry_end=0.62, wob=9, base=0.36, speck=0.10),
]
PORT = [
    dict(yc=0.40, hw=150, xs=0.02, xe=0.84, color=DEEP, light=MAIN, dry_end=0.30),
    dict(yc=0.50, hw=185, xs=0.0, xe=0.95, color=MAIN, light=BRAND, dry_end=0.34),
    dict(yc=0.60, hw=150, xs=0.06, xe=0.90, color=DEEP, light=BRAND, dry_end=0.30),
    dict(yc=0.46, hw=24, xs=0.22, xe=0.84, color=LIME, light=PALE, dry_end=0.60, wob=10, base=0.34, speck=0.09),
    dict(yc=0.57, hw=18, xs=0.14, xe=0.76, color=LIGHT, light=PALE, dry_end=0.62, wob=9, base=0.36, speck=0.10),
]
SPL = [dict(cx=0.14, cy=0.55, sx=45, sy=60, n=34, color=MAIN, rmax=5), dict(cx=0.90, cy=0.40, sx=50, sy=55, n=30, color=DEEP, rmax=5)]

if __name__ == "__main__":
    d = sys.argv[1]
    compose(f"{d}/mv-landscape.png", f"{d}/c-landscape.png", -17, LAND, SPL, 41)
    compose(f"{d}/mv-portrait.png", f"{d}/c-portrait.png", -19, PORT, SPL, 52)
