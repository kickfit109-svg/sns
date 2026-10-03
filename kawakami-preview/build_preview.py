#!/usr/bin/env python3
"""川上かずき公式サイトの「プレビュー用HTML」を作るスクリプト。

kawakami/ の各ページを、CSS・JavaScript・画像をすべて埋め込んだ
1ファイルのHTMLに変換します。サーバー不要で、ダブルクリックやスマホでそのまま開けます。

使い方:
    python3 kawakami-preview/build_preview.py
出力:
    kawakami-preview/index.html     … トップページ（これを開けばOK）
    kawakami-preview/gikai.html     … 八王子市議会ガイド
    kawakami-preview/privacy.html   … プライバシーポリシー
    kawakami-preview/thanks.html    … ご意見送信後の画面

※ 公開用ではありません（公開は kawakami/ フォルダを使います）。
※ フォームはプレビューでは送信されず、送信完了画面に移動するだけです。
"""
import base64
import mimetypes
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "kawakami"
OUT = Path(__file__).resolve().parent

PAGES = {
    "index.html": "index.html",
    "gikai/index.html": "gikai.html",
    "privacy/index.html": "privacy.html",
    "thanks/index.html": "thanks.html",
}
# サイト内リンク → プレビューのファイル名
ROUTES = {"": "index.html", "gikai/": "gikai.html", "privacy/": "privacy.html", "thanks/": "thanks.html"}

mimetypes.add_type("image/webp", ".webp")
_cache = {}


def data_uri(path: Path) -> str:
    if path not in _cache:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        _cache[path] = f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()
    return _cache[path]


def is_local(url: str) -> bool:
    return not re.match(r"^(https?:|mailto:|tel:|data:|#|//)", url)


def resolve(page_dir: Path, url: str) -> Path:
    url = url.split("#")[0].split("?")[0]
    return (SITE / url.lstrip("/")) if url.startswith("/") else (page_dir / url).resolve()


def inline_css(css: str) -> str:
    def repl(m):
        p = (SITE / "assets" / m.group(2)).resolve()
        return f'url("{data_uri(p)}")' if p.exists() else m.group(0)
    return re.sub(r'url\((["\']?)([^)"\']+)\1\)', repl, css)


def page_link(page_dir: Path, href: str) -> str:
    """サイト内のページリンクをプレビューのファイル名に置き換える"""
    path, _, frag = href.partition("#")
    target = (page_dir / path).resolve() if path else page_dir
    try:
        rel = target.relative_to(SITE).as_posix()
    except ValueError:
        return href
    rel = "" if rel == "." else rel.rstrip("/") + "/"
    if rel in ROUTES:
        return ROUTES[rel] + (f"#{frag}" if frag else "")
    return href


def build(src_rel: str, out_name: str) -> int:
    src = SITE / src_rel
    page_dir = src.parent
    html = src.read_text(encoding="utf-8")

    # CSS / JS を埋め込む（JS は本文の最後へ）
    css = inline_css((SITE / "assets/style.css").read_text(encoding="utf-8"))
    js = (SITE / "assets/main.js").read_text(encoding="utf-8")
    html = re.sub(r'<link rel="stylesheet" href="[^"]*assets/style\.css">', lambda _: f"<style>\n{css}\n</style>", html)
    html = re.sub(r'<script src="[^"]*assets/main\.js" defer></script>\n?', "", html)
    html = html.replace("</body>", f"<script>\n{js}\n</script>\n</body>")
    html = re.sub(r'<link rel="preload"[^>]*>\n?', "", html)

    # 画像（src / srcset / imagesrcset / アイコン）を埋め込む
    def img_attr(m):
        attr, val = m.group(1), m.group(2)
        if attr in ("srcset", "imagesrcset"):
            parts = []
            for item in val.split(","):
                bits = item.strip().split(" ", 1)
                if is_local(bits[0]):
                    p = resolve(page_dir, bits[0])
                    if p.exists():
                        bits[0] = data_uri(p)
                parts.append(" ".join(bits))
            return f'{attr}="{", ".join(parts)}"'
        if is_local(val) and re.search(r"\.(webp|jpe?g|png|svg|gif)$", val.split("#")[0]):
            p = resolve(page_dir, val)
            if p.exists():
                return f'{attr}="{data_uri(p)}"'
        return m.group(0)
    html = re.sub(r'\b(src|srcset|imagesrcset)="([^"]+)"', img_attr, html)
    html = re.sub(r'(<link rel="(?:icon|apple-touch-icon)"[^>]*\bhref=")([^"]+)(")',
                  lambda m: m.group(1) + (data_uri(resolve(page_dir, m.group(2))) if is_local(m.group(2)) else m.group(2)) + m.group(3), html)

    # ページ間リンク
    def href(m):
        val = m.group(1)
        if not is_local(val) or val.startswith("#"):
            return m.group(0)
        return f'href="{page_link(page_dir, val)}"'
    html = re.sub(r'href="([^"]+)"', href, html)

    # フォーム：プレビューでは送信せず完了画面へ
    html = html.replace('method="POST" action="thanks/"', 'method="GET" action="thanks.html"')

    # プレビューの目印
    badge = ('<div style="position:fixed;left:10px;bottom:10px;z-index:99;padding:6px 12px;border-radius:999px;'
             'background:rgba(16,37,26,.85);color:#fff;font:700 11px/1.4 sans-serif;letter-spacing:.04em;pointer-events:none">'
             'プレビュー（フォームは送信されません）</div>\n')
    html = html.replace("</body>", badge + "</body>")

    (OUT / out_name).write_text(html, encoding="utf-8")
    return len(html.encode("utf-8"))


if __name__ == "__main__":
    for src, out in PAGES.items():
        size = build(src, out)
        print(f"{out:14s} {size / 1024 / 1024:.2f} MB")
