"""Claude を使った投稿文の自動生成。

学習済みパターンプロファイルをプロンプトに埋め込み、各SNSの特性に
最適化した投稿文を生成する。ANTHROPIC_API_KEY が無い場合は、
テンプレートベースのオフライン下書きを生成する（動作確認用）。
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime

from ..config import DEFAULT_MODEL, PLATFORM_LIMITS, get_anthropic_key
from .analyzer import PatternProfile, get_profile


@dataclass
class Draft:
    platform: str
    topic: str
    # X/Threads はスレッド対応: parts が2つ以上ならスレッド
    parts: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    title: str = ""  # note 用
    created_at: str = ""
    model: str = ""

    @property
    def full_text(self) -> str:
        body = "\n\n".join(self.parts)
        if self.hashtags:
            body += "\n\n" + " ".join(self.hashtags)
        return body


PLATFORM_STYLE = {
    "x": (
        "Xでは280文字制限を意識し、1文目のフックで手を止めさせる。"
        "長い場合は複数ツイートのスレッドに分割する。ハッシュタグは1-2個。"
    ),
    "threads": (
        "Threadsは500文字まで。会話的でカジュアルなトーン。"
        "共感を誘う問いかけや本音を織り交ぜる。ハッシュタグは控えめに。"
    ),
    "note": (
        "noteは長文記事。魅力的なタイトルと、導入→本論→まとめの構成で"
        "見出し(##)を使い読みやすく。1000〜2000字程度の読み応えを目安に。"
    ),
}


def _build_prompt(topic: str, platform: str, profile: PatternProfile, tone: str | None) -> str:
    limit = PLATFORM_LIMITS[platform]
    style = PLATFORM_STYLE[platform]
    tone_line = f"\n指定トーン: {tone}" if tone else ""

    schema = _output_schema(platform)

    return f"""あなたはSNS運用のプロです。以下の『伸びるパターン』の学習結果を最大限活用し、
「{platform}」で伸びる投稿を作成してください。

{profile.to_prompt_block()}

## プラットフォーム特性
{style}
- 文字数上限: {"実質無制限" if limit["max_chars"] == 0 else str(limit["max_chars"]) + "文字/投稿"}

## お題
{topic}{tone_line}

## 制約
- 学習した伸びるフックの型を必ず1文目に適用すること。
- 実際に読者が行動したくなる投稿にすること。
- 誇大広告・虚偽・誤解を招く表現は避けること。

## 出力形式
必ず次のJSONのみを出力してください（前後に説明文を付けない）:
{schema}
"""


def _output_schema(platform: str) -> str:
    if platform == "note":
        return json.dumps(
            {"title": "記事タイトル", "parts": ["本文（Markdown、見出し##可）"], "hashtags": ["#タグ"]},
            ensure_ascii=False,
            indent=2,
        )
    return json.dumps(
        {
            "parts": ["1つ目の投稿（スレッドなら2つ目以降も配列で）"],
            "hashtags": ["#タグ1"],
        },
        ensure_ascii=False,
        indent=2,
    )


def _extract_json(text: str) -> dict:
    """モデル出力からJSONブロックを頑健に抽出。"""
    text = text.strip()
    # ```json ... ``` を剥がす
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)
    return json.loads(text)


def generate_draft(
    topic: str,
    platform: str,
    tone: str | None = None,
    profile: PatternProfile | None = None,
) -> Draft:
    """1プラットフォーム分の下書きを生成。"""
    profile = profile or get_profile(platform)
    api_key = get_anthropic_key()

    if not api_key:
        return _offline_draft(topic, platform, profile)

    prompt = _build_prompt(topic, platform, profile, tone)

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(block.text for block in resp.content if block.type == "text")
        data = _extract_json(raw)
    except Exception as e:  # 生成失敗時はオフライン下書きにフォールバック
        draft = _offline_draft(topic, platform, profile)
        draft.parts.append(f"（※Claude生成に失敗したためテンプレ下書きです: {e}）")
        return draft

    return Draft(
        platform=platform,
        topic=topic,
        parts=[p for p in data.get("parts", []) if p.strip()],
        hashtags=data.get("hashtags", []),
        title=data.get("title", ""),
        created_at=datetime.now().isoformat(timespec="seconds"),
        model=DEFAULT_MODEL,
    )


def _offline_draft(topic: str, platform: str, profile: PatternProfile) -> Draft:
    """APIキーが無い場合のテンプレ下書き（動作確認・オフライン用）。"""
    hook = profile.best_hooks[0] if profile.best_hooks else "結論ファースト"
    if platform == "note":
        parts = [
            f"## はじめに\n\n「{topic}」について、実践してわかったことをまとめます。\n\n"
            f"## 本論\n\n（ここに本文。フックの型: {hook}）\n\n"
            f"## まとめ\n\n最後まで読んでいただきありがとうございました。"
        ]
        return Draft(
            platform=platform,
            topic=topic,
            parts=parts,
            hashtags=["#" + topic.replace(" ", "")[:10]],
            title=f"{topic}｜実践してわかったこと",
            created_at=datetime.now().isoformat(timespec="seconds"),
            model="offline-template",
        )

    parts = [
        f"【{topic}】\n\n結論から言うと、これを知らないと損します。\n\n"
        f"（フックの型: {hook} を1文目に適用）\n\n"
        f"続きはリプ欄で👇"
    ]
    return Draft(
        platform=platform,
        topic=topic,
        parts=parts,
        hashtags=["#" + topic.replace(" ", "")[:10]],
        created_at=datetime.now().isoformat(timespec="seconds"),
        model="offline-template",
    )


def generate_all(topic: str, platforms: list[str], tone: str | None = None) -> dict[str, Draft]:
    return {p: generate_draft(topic, p, tone=tone) for p in platforms}


def draft_to_dict(draft: Draft) -> dict:
    return asdict(draft)
