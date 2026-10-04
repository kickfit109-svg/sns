# 筆のストロークを描く関数（compose_brush.py から使います）
"""筆で塗ったような緑のストローク背景を生成する（透過PNG）。
横向きにストロークを描いてから回転させ、毛筆のかすれ・飛沫を乗せる。"""
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

def norm(a):
    a = a - a.min()
    return a / (a.max() + 1e-9)

def bristle(h, w, rng, sy=1.1, sx=60):
    n = rng.random((h, w))
    n = gaussian_filter(n, sigma=(sy, sx))
    n2 = gaussian_filter(rng.random((h, w)), sigma=(6, 140))
    return norm(0.7 * norm(n) + 0.3 * norm(n2))

def smooth1d(n, rng, sigma):
    return gaussian_filter(rng.random(n), sigma)

def draw_stroke(canvas, rng, yc, hw, xs, xe, color, light, dry_end=0.3, dry_start=0.10, wob=18, speck=0.014, base=0.04):
    H, W = canvas.shape[:2]
    x0, x1 = max(0, int(xs - 40)), min(W, int(xe + 40))
    y0, y1 = max(0, int(yc - hw * 1.6)), min(H, int(yc + hw * 1.6))
    h, w = y1 - y0, x1 - x0
    if h <= 0 or w <= 0:
        return
    xs_ = np.arange(x0 - 0, x1)
    t = (xs_ - xs) / max(1, (xe - xs))                       # 0..1 along stroke
    # 幅の変化（入りは素早く、抜きは細く）
    prof = np.clip(np.minimum((t + 0.06) / 0.08, 1), 0, 1) * np.clip((1.12 - t) / 0.4, 0.45, 1)
    prof *= 1 + 0.10 * (norm(smooth1d(w, rng, 25)) - 0.5)
    wobble = (norm(smooth1d(w, rng, 120)) - 0.5) * wob
    hw_x = hw * prof
    ys = np.arange(y0, y1)[:, None]
    dy = np.abs(ys - (yc + wobble)[None, :])
    inside = np.clip((hw_x[None, :] - dy) / 3.0, 0, 1)      # 柔らかい縁
    # かすれ（端ほど・縁ほど毛が割れる）
    B = bristle(h, w, rng)
    L = max(1, (xe - xs))
    off_s = (norm(gaussian_filter(rng.random(h), 2.5)) - 0.5) * 0.10 + (norm(gaussian_filter(rng.random(h), 14)) - 0.5) * 0.08
    off_e = (norm(gaussian_filter(rng.random(h), 2.0)) - 0.5) * 0.22 + (norm(gaussian_filter(rng.random(h), 18)) - 0.5) * 0.12
    tt = t[None, :] - off_s[:, None]
    te = t[None, :] - off_e[:, None]
    dry = np.clip((te - (1 - dry_end)) / dry_end, 0, 1) ** 1.3 * 0.95
    dry = dry + np.clip((dry_start - tt) / dry_start, 0, 1) * 0.9
    dry = np.where(tt < -0.01, 2.0, dry)
    dry = np.where(te > 1.02, 2.0, dry)
    edge = np.clip(dy / np.maximum(hw_x[None, :], 1), 0, 1) ** 5 * 0.55
    thresh = dry + edge + base
    a = inside * np.clip((B - thresh) * 9, 0, 1)
    # 紙のかすれ（小さな白抜けの粒）
    g = gaussian_filter(rng.random((h, w)), 1.1)
    q = np.quantile(g[::4, ::4], speck)
    a *= np.clip((g - q) * 60, 0, 1)
    # 色の濃淡（毛の筋で明暗をつける）
    B2 = bristle(h, w, rng, sy=0.9, sx=90)
    mix = np.clip((B2 - 0.45) * 2.2, 0, 1)[..., None]
    col = np.array(color, float)[None, None, :] * (1 - mix) + np.array(light, float)[None, None, :] * mix
    region = canvas[y0:y1, x0:x1]
    a3 = a[..., None]
    region[..., :3] = region[..., :3] * (1 - a3) + col * a3
    region[..., 3:] = region[..., 3:] * (1 - a3) + a3

def splatter(canvas, rng, cx, cy, spread_x, spread_y, n, color, rmax=7):
    H, W = canvas.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    for _ in range(n):
        x = cx + rng.normal(0, spread_x)
        y = cy + rng.normal(0, spread_y)
        r = max(1.2, abs(rng.normal(0, rmax / 2.2)))
        stretch = 1 + rng.random() * 3.5                     # 進行方向に伸びた飛沫
        x0, x1 = int(max(0, x - r * stretch - 2)), int(min(W, x + r * stretch + 2))
        y0, y1 = int(max(0, y - r - 2)), int(min(H, y + r + 2))
        if x1 <= x0 or y1 <= y0:
            continue
        sx = xx[y0:y1, x0:x1]; sy = yy[y0:y1, x0:x1]
        d = ((sx - x) / (r * stretch)) ** 2 + ((sy - y) / r) ** 2
        a = np.clip((1 - d) * 3, 0, 1)[..., None]
        region = canvas[y0:y1, x0:x1]
        region[..., :3] = region[..., :3] * (1 - a) + np.array(color, float) * a
        region[..., 3:] = np.maximum(region[..., 3:], a)

def build(W, H, angle, strokes, splats, seed, out):
    rng = np.random.default_rng(seed)
    # 回転しても欠けないよう大きめに描く
    L = int(np.hypot(W, H)) + 200
    canvas = np.zeros((L, L, 4), float)
    for s in strokes:
        draw_stroke(canvas, rng, **{k: (v * L if k in ("yc", "xs", "xe") else v) for k, v in s.items()})
    for sp in splats:
        splatter(canvas, rng, sp["cx"] * L, sp["cy"] * L, sp["sx"], sp["sy"], sp["n"], sp["color"], sp.get("rmax", 7))
    img = Image.fromarray(np.clip(canvas * [1, 1, 1, 255], 0, 255).astype(np.uint8), "RGBA")
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False)
    l = (L - W) // 2; t = (L - H) // 2
    img = img.crop((l, t, l + W, t + H))
    img.save(out)
    print("saved", out, img.size)

DEEP = (0, 70, 35); MAIN = (0, 112, 50); BRAND = (0, 150, 62); LIGHT = (60, 190, 95); PALE = (150, 220, 150)

def strokes_set(scale):
    s = scale
    return [
        dict(yc=0.34, hw=150 * s, xs=0.12, xe=0.86, color=DEEP, light=MAIN, dry_end=0.30),
        dict(yc=0.43, hw=170 * s, xs=0.05, xe=0.92, color=MAIN, light=BRAND, dry_end=0.34),
        dict(yc=0.52, hw=160 * s, xs=0.10, xe=0.95, color=DEEP, light=BRAND, dry_end=0.28),
        dict(yc=0.61, hw=150 * s, xs=0.04, xe=0.88, color=MAIN, light=LIGHT, dry_end=0.33),
        dict(yc=0.69, hw=120 * s, xs=0.14, xe=0.97, color=BRAND, light=PALE, dry_end=0.36),
        dict(yc=0.40, hw=26 * s, xs=0.26, xe=0.84, color=BRAND, light=LIGHT, dry_end=0.6, wob=10, base=0.32, speck=0.08),
        dict(yc=0.47, hw=18 * s, xs=0.38, xe=0.90, color=LIGHT, light=PALE, dry_end=0.6, wob=8, base=0.38, speck=0.1),
        dict(yc=0.57, hw=22 * s, xs=0.18, xe=0.78, color=LIGHT, light=PALE, dry_end=0.65, wob=10, base=0.34, speck=0.1),
        dict(yc=0.30, hw=60 * s, xs=0.22, xe=0.70, color=MAIN, light=BRAND, dry_end=0.5, wob=14, base=0.18),
    ]

if __name__ == "__main__":
    out_dir = sys.argv[1]
    splats = [
        dict(cx=0.86, cy=0.40, sx=50, sy=70, n=70, color=MAIN),
        dict(cx=0.90, cy=0.58, sx=60, sy=60, n=60, color=DEEP),
        dict(cx=0.14, cy=0.36, sx=40, sy=60, n=40, color=DEEP, rmax=5),
        dict(cx=0.93, cy=0.68, sx=40, sy=40, n=40, color=BRAND),
    ]
    port = [dict(d, yc=d["yc"] - 0.06, xs=max(0.0, d["xs"] - 0.08)) for d in strokes_set(1.3)]
    port.append(dict(yc=0.25, hw=150 * 1.3, xs=0.0, xe=0.78, color=DEEP, light=MAIN, dry_end=0.32))
    build(1200, 1700, 30, port, splats, 7, f"{out_dir}/brush-portrait.png")
    land = [dict(d, yc=d["yc"] + 0.06, xe=min(0.9, d["xe"])) for d in strokes_set(1.4)]
    build(2400, 1300, 22, land, splats, 11, f"{out_dir}/brush-landscape.png")
