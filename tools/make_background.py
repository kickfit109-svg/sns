"""トップページ用の背景を作るスクリプト（八王子の山並み＋地図の等高線）。

使い方:  pip install numpy scipy matplotlib pillow
         python3 tools/make_background.py kawakami/assets/img/
         （下地のPNGが出力されます。続けて tools/compose_brush.py で筆を重ね、WebPに変換して mv-landscape.webp / mv-portrait.webp に置き換える）

トップページ用の背景：八王子の山並み＋地図の等高線をモチーフにした緑のグラフィック。
（筆のストロークではなく、等高線・光・山の稜線で構成）"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter


def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255


def build(W, H, peak, seed, out, ridge_base, line_density=30):
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, W)[None, :].repeat(H, 0)
    y = np.linspace(0, 1, H)[:, None].repeat(W, 1)
    aspect = W / H
    cx, cy = peak

    # ---- ベース：深い緑から鮮やかな緑へ。ピークのまわりに明るい光 ----
    c_dark, c_mid, c_main, c_glow = hex2rgb("#03321d"), hex2rgb("#06683a"), hex2rgb("#00a041"), hex2rgb("#7ff0a6")
    t = np.clip(0.80 * x + 0.35 * (1 - y), 0, 1.4)
    base = np.where(t[..., None] < 0.7,
                    c_dark + (c_mid - c_dark) * (t[..., None] / 0.7),
                    c_mid + (c_main - c_mid) * np.clip((t[..., None] - 0.7) / 0.7, 0, 1))
    r2 = ((x - cx) * aspect) ** 2 / (2 * 0.34 ** 2) + (y - cy) ** 2 / (2 * 0.46 ** 2)
    glow = np.exp(-r2)[..., None]
    img = base * (1 - 0.62 * glow) + c_glow * 0.62 * glow
    # 薄い光の輪（ピークを囲む）
    ring = np.exp(-(((np.sqrt(((x - cx) * aspect) ** 2 + ((y - cy) * 1.0) ** 2) - 0.46) / 0.012) ** 2))[..., None]
    img = img + ring * 0.07
    img += rng.normal(0, 0.006, (H, W, 1))  # バンディング防止の微細なノイズ
    img = np.clip(img, 0, 1)

    # ---- 地形（等高線用）：ピーク＋副ピーク＋ゆるいうねり ----
    def bump(px, py, sx, sy, a):
        return a * np.exp(-(((x - px) * aspect) ** 2 / (2 * sx ** 2) + (y - py) ** 2 / (2 * sy ** 2)))
    from scipy.ndimage import zoom
    noise = zoom(gaussian_filter(rng.random((H // 8, W // 8)), 5), (H / (H // 8), W / (W // 8)), order=1)[:H, :W]
    noise = (noise - noise.min()) / (noise.max() - noise.min())
    h = (bump(cx, cy, 0.30, 0.55, 1.0) + bump(cx - 0.36, cy + 0.22, 0.22, 0.38, 0.55)
         + bump(cx + 0.30, cy + 0.30, 0.18, 0.30, 0.45) + bump(cx - 0.62, cy - 0.05, 0.16, 0.30, 0.30)
         + 0.28 * noise)

    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    ax.imshow(img, extent=(0, W, H, 0), interpolation="bilinear", aspect="auto")

    levels = np.linspace(h.min() + 0.04, h.max() - 0.03, line_density)
    minor = [l for i, l in enumerate(levels) if i % 5 != 0]
    major = [l for i, l in enumerate(levels) if i % 5 == 0]
    X, Y = np.meshgrid(np.arange(W), np.arange(H))
    ax.contour(X, Y, h, levels=minor, colors=[(1, 1, 1, 0.11)], linewidths=1.1)
    ax.contour(X, Y, h, levels=major, colors=[(1, 1, 1, 0.24)], linewidths=2.0)

    # ---- 山の稜線（手前ほど濃く・鮮やかに） ----
    xs = np.linspace(0, W, 400)
    def ridge(base_y, amp, seed2, color, alpha):
        r2 = np.random.default_rng(seed2)
        ph = r2.random(5) * 6.28
        yy = base_y + amp * (0.5 * np.sin(xs / W * 5.2 + ph[0]) + 0.3 * np.sin(xs / W * 11 + ph[1]) + 0.2 * np.sin(xs / W * 23 + ph[2]))
        ax.fill_between(xs, yy, H, color=color, alpha=alpha, lw=0)
        ax.plot(xs, yy, color=(1, 1, 1, 0.18), lw=1.4)
    rb = ridge_base
    ridge(H * (rb - 0.07), H * 0.045, 3, hex2rgb("#0a7a43"), 0.55)
    ridge(H * (rb - 0.02), H * 0.040, 5, hex2rgb("#06603a"), 0.78)
    ridge(H * (rb + 0.05), H * 0.035, 8, hex2rgb("#043d26"), 0.92)

    fig.savefig(out, dpi=100)
    plt.close(fig)
    print("saved", out, (W, H))


if __name__ == "__main__":
    d = sys.argv[1]
    build(1920, 1040, (0.66, 0.40), 21, f"{d}/mv-landscape.png", 0.86)
    build(1000, 1560, (0.50, 0.36), 34, f"{d}/mv-portrait.png", 0.90, line_density=26)
