"""snsgrow CLI エントリポイント。

サブコマンド:
  learn     過去投稿CSVから伸びるパターンを学習
  patterns  学習済みパターンを表示
  generate  トピックから各SNS向け下書きを生成
  post      生成済み下書きをプレビュー → 投稿
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from . import __version__
from .config import OUT_DIR, PLATFORMS, ensure_dirs
from .core import analyzer, scheduler
from .core.generator import Draft, draft_to_dict, generate_all
from .platforms import get_poster


def _expand_platforms(value: str) -> list[str]:
    if value == "all":
        return list(PLATFORMS)
    parts = [p.strip() for p in value.split(",") if p.strip()]
    for p in parts:
        if p not in PLATFORMS:
            raise SystemExit(f"未知のプラットフォーム: {p}（有効: {', '.join(PLATFORMS)}, all）")
    return parts


# ---------- learn ----------
def cmd_learn(args: argparse.Namespace) -> int:
    ensure_dirs()
    platforms = _expand_platforms(args.platform)
    profiles = analyzer.load_profiles()

    for platform in platforms:
        try:
            learned = analyzer.learn_from_csv(args.input, platform)
        except Exception as e:
            print(f"[{platform}] 学習エラー: {e}", file=sys.stderr)
            return 1

        if args.hybrid:
            learned = analyzer.merge_profiles(learned, analyzer.default_profile(platform))

        profiles[platform] = learned
        print(f"[{platform}] 学習完了: {learned.sample_size}件から抽出")
        print(learned.to_prompt_block())
        print()

    analyzer.save_profiles(profiles)
    print(f"→ パターンを保存しました: {analyzer.PATTERNS_PATH}")
    return 0


# ---------- patterns ----------
def cmd_patterns(args: argparse.Namespace) -> int:
    profiles = analyzer.load_profiles()
    if not profiles:
        print("学習済みパターンはまだありません。まず `learn` を実行するか、既定パターンで生成できます。")
        for p in PLATFORMS:
            print()
            print(analyzer.default_profile(p).to_prompt_block())
        return 0
    for platform, profile in profiles.items():
        print(profile.to_prompt_block())
        print()
    return 0


# ---------- generate ----------
def cmd_generate(args: argparse.Namespace) -> int:
    ensure_dirs()
    platforms = _expand_platforms(args.platform)
    drafts = generate_all(args.topic, platforms, tone=args.tone)

    payload = {
        "topic": args.topic,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "drafts": {p: draft_to_dict(d) for p, d in drafts.items()},
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"draft_{stamp}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = OUT_DIR / "latest.json"
    latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for platform, draft in drafts.items():
        _preview(platform, draft)

    print(f"\n→ 保存しました: {out_path}")
    print(f"→ 投稿するには: python -m snsgrow post --draft {latest} --platform <x|threads|note|all>")
    return 0


def _preview(platform: str, draft: Draft) -> None:
    print("=" * 60)
    print(f"[{platform.upper()}] (model={draft.model})")
    print("-" * 60)
    if draft.title:
        print(f"タイトル: {draft.title}")
    for i, part in enumerate(draft.parts, 1):
        prefix = f"({i}/{len(draft.parts)}) " if len(draft.parts) > 1 else ""
        print(f"{prefix}{part}")
        if len(draft.parts) > 1:
            print("  ---")
    if draft.hashtags:
        print("タグ: " + " ".join(draft.hashtags))


# ---------- post ----------
def cmd_post(args: argparse.Namespace) -> int:
    draft_path = Path(args.draft)
    if not draft_path.exists():
        print(f"下書きが見つかりません: {draft_path}", file=sys.stderr)
        return 1

    payload = json.loads(draft_path.read_text(encoding="utf-8"))
    all_drafts = payload.get("drafts", {})
    platforms = _expand_platforms(args.platform)

    exit_code = 0
    for platform in platforms:
        if platform not in all_drafts:
            print(f"[{platform}] この下書きには {platform} が含まれていません。スキップ。")
            continue

        draft = Draft(**all_drafts[platform])
        poster = get_poster(platform)

        print()
        _preview(platform, draft)

        if args.schedule == "optimal":
            when = scheduler.next_optimal_time(platform)
            print(f"※ 推奨投稿時刻: {when.strftime('%Y-%m-%d %H:%M')}（この時刻に再実行を推奨）")

        # 投稿確認
        if not args.yes:
            mode = "自動投稿" if poster.available() else "下書き保存"
            ans = input(f"\n[{platform}] {mode}しますか? [y/N]: ").strip().lower()
            if ans not in ("y", "yes"):
                print(f"[{platform}] スキップしました。")
                continue

        result = poster.post(draft)
        icon = {"posted": "✅", "draft": "📝", "error": "❌"}.get(result.mode, "•")
        print(f"{icon} [{platform}] {result.mode}: {result.message}")
        if result.url:
            print(f"   URL/パス: {result.url}")
        if result.mode == "error":
            exit_code = 1

    return exit_code


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="snsgrow",
        description="SNS成長パターン学習 & 自動投稿ツール (Threads / X / note)",
    )
    p.add_argument("--version", action="version", version=f"snsgrow {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("learn", help="過去投稿CSVから伸びるパターンを学習")
    sp.add_argument("--input", "-i", required=True, help="投稿実績のCSVパス")
    sp.add_argument("--platform", "-p", default="x", help="x|threads|note|all またはカンマ区切り")
    sp.add_argument("--hybrid", action="store_true", help="学習結果を一般パターン知識で補完")
    sp.set_defaults(func=cmd_learn)

    sp = sub.add_parser("patterns", help="学習済みパターンを表示")
    sp.set_defaults(func=cmd_patterns)

    sp = sub.add_parser("generate", help="トピックから各SNS向け下書きを生成")
    sp.add_argument("--topic", "-t", required=True, help="投稿のお題")
    sp.add_argument("--platform", "-p", default="all", help="x|threads|note|all またはカンマ区切り")
    sp.add_argument("--tone", help="トーン指定（例: カジュアル / 丁寧 / 熱量高め）")
    sp.set_defaults(func=cmd_generate)

    sp = sub.add_parser("post", help="生成済み下書きをプレビュー → 投稿")
    sp.add_argument("--draft", "-d", default=str(OUT_DIR / "latest.json"), help="下書きJSONパス")
    sp.add_argument("--platform", "-p", default="all", help="x|threads|note|all またはカンマ区切り")
    sp.add_argument("--yes", "-y", action="store_true", help="確認プロンプトをスキップして投稿")
    sp.add_argument("--schedule", choices=["now", "optimal"], default="now", help="投稿タイミング")
    sp.set_defaults(func=cmd_post)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
