"""伸びる投稿パターンの学習・分析。

過去投稿の実績CSVを読み込み、「伸びた投稿」に共通する特徴を抽出して
パターンプロファイル（patterns.json）に保存する。
実績が無くても、一般的な「伸びる型」の既定知識で補完できる。
"""
from __future__ import annotations

import csv
import json
import re
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from ..config import PATTERNS_PATH

# 一般的に「伸びやすい」とされるフックの型（実績が無い場合の補完に使用）
DEFAULT_HOOKS = [
    "数字を冒頭に置く（例: 3つの理由 / 月5万）",
    "常識への逆張り（例: 〜はもうやめよう）",
    "読者の悩みへの直接呼びかけ（例: 〜で悩んでいませんか?）",
    "結論ファースト（例: 結論から言うと〜）",
    "実体験・失敗談の告白（例: 100万溶かして学んだ）",
    "限定・希少性（例: 知らないと損する）",
]

# エンゲージメントに使う可能性のあるカラム名の候補（表記ゆれ吸収）
ENGAGEMENT_KEYS = ["likes", "like", "いいね", "favorites", "fav"]
IMPRESSION_KEYS = ["impressions", "impression", "views", "view", "インプレッション", "表示"]
TEXT_KEYS = ["text", "body", "content", "本文", "投稿", "post"]
DATE_KEYS = ["date", "datetime", "created_at", "posted_at", "日時", "日付"]

HASHTAG_RE = re.compile(r"#\S+")
NUMBER_RE = re.compile(r"[0-9０-９]")


@dataclass
class PatternProfile:
    """学習結果。生成プロンプトに渡すための特徴サマリ。"""

    platform: str
    sample_size: int = 0
    source: str = "default"  # "learned" | "default" | "hybrid"
    # 伸びた投稿の特徴
    top_avg_len: float = 0.0
    all_avg_len: float = 0.0
    best_hooks: list[str] = field(default_factory=list)
    best_hours: list[int] = field(default_factory=list)
    hashtag_usage: float = 0.0  # 伸びた投稿でのハッシュタグ平均個数
    uses_numbers_ratio: float = 0.0  # 伸びた投稿で冒頭に数字がある割合
    top_examples: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        """生成プロンプトに埋め込む自然文サマリ。"""
        lines = [f"# 学習済み『伸びるパターン』（{self.platform} / source={self.source} / n={self.sample_size}）"]
        if self.top_avg_len:
            lines.append(f"- 伸びた投稿の平均文字数: 約{int(self.top_avg_len)}文字")
        if self.best_hooks:
            lines.append("- 効果的だったフックの型:")
            lines.extend(f"    - {h}" for h in self.best_hooks)
        if self.best_hours:
            hrs = "、".join(f"{h}時台" for h in self.best_hours)
            lines.append(f"- 反応が良かった投稿時間帯: {hrs}")
        if self.hashtag_usage:
            lines.append(f"- ハッシュタグは平均{self.hashtag_usage:.1f}個が好反応")
        if self.uses_numbers_ratio:
            lines.append(f"- 伸びた投稿の{int(self.uses_numbers_ratio * 100)}%が冒頭に具体的な数字を含む")
        if self.top_examples:
            lines.append("- 実際に伸びた投稿の冒頭例:")
            lines.extend(f'    - "{ex}"' for ex in self.top_examples)
        for n in self.notes:
            lines.append(f"- {n}")
        return "\n".join(lines)


def _find_key(row: dict, candidates: list[str]) -> str | None:
    lowered = {k.lower().strip(): k for k in row.keys()}
    for cand in candidates:
        if cand.lower() in lowered:
            return lowered[cand.lower()]
    return None


def _parse_hour(value: str) -> int | None:
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).hour
        except ValueError:
            continue
    # 単純に "HH:MM" だけのケース
    m = re.search(r"\b(\d{1,2}):\d{2}\b", value)
    if m:
        return int(m.group(1))
    return None


def _engagement_score(row: dict, like_key: str | None, imp_key: str | None) -> float:
    """エンゲージメント率(またはいいね数)を算出。"""
    def _num(key: str | None) -> float:
        if not key:
            return 0.0
        raw = str(row.get(key, "")).replace(",", "").strip()
        try:
            return float(raw)
        except ValueError:
            return 0.0

    likes = _num(like_key)
    imps = _num(imp_key)
    if imps > 0:
        return likes / imps  # エンゲージメント率
    return likes  # インプレッションが無ければ生いいね数


def default_profile(platform: str) -> PatternProfile:
    """実績が無い場合の既定パターン。"""
    return PatternProfile(
        platform=platform,
        sample_size=0,
        source="default",
        best_hooks=DEFAULT_HOOKS,
        best_hours=[7, 12, 21],  # 通勤・昼休み・就寝前の一般的な好反応帯
        hashtag_usage=2.0 if platform != "note" else 3.0,
        uses_numbers_ratio=0.5,
        notes=[
            "1文目（フック）で結論や意外性を提示し、続きを読ませる。",
            "改行を多めに使い、スマホで読みやすい余白を作る。",
            "最後にリプ・保存・フォローなど具体的な行動を促す。",
        ],
    )


def learn_from_csv(csv_path: str | Path, platform: str) -> PatternProfile:
    """CSVから伸びるパターンを学習する。

    CSVには少なくとも本文列と、いいね/インプレッション列があることを想定。
    列名は表記ゆれを吸収する（日本語ヘッダーも可）。
    """
    csv_path = Path(csv_path)
    rows: list[dict] = []
    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if any(v.strip() for v in r.values())]

    if not rows:
        raise ValueError(f"CSVにデータ行がありません: {csv_path}")

    sample = rows[0]
    text_key = _find_key(sample, TEXT_KEYS)
    like_key = _find_key(sample, ENGAGEMENT_KEYS)
    imp_key = _find_key(sample, IMPRESSION_KEYS)
    date_key = _find_key(sample, DATE_KEYS)

    if not text_key:
        raise ValueError(
            "本文の列が見つかりません。'text' / '本文' / 'content' 等の列名を用意してください。"
        )
    if not like_key:
        raise ValueError(
            "エンゲージメントの列が見つかりません。'likes' / 'いいね' 等の列名を用意してください。"
        )

    # スコアリング
    scored = []
    for r in rows:
        text = (r.get(text_key) or "").strip()
        if not text:
            continue
        score = _engagement_score(r, like_key, imp_key)
        hour = _parse_hour(r.get(date_key, "")) if date_key else None
        scored.append({"text": text, "score": score, "hour": hour})

    if not scored:
        raise ValueError("有効な投稿本文がありませんでした。")

    scored.sort(key=lambda x: x["score"], reverse=True)
    n = len(scored)
    top_n = max(1, round(n * 0.25))  # 上位25%を「伸びた投稿」とみなす
    top = scored[:top_n]

    all_lens = [len(s["text"]) for s in scored]
    top_lens = [len(s["text"]) for s in top]

    # ハッシュタグ・数字の傾向
    hashtag_counts = [len(HASHTAG_RE.findall(s["text"])) for s in top]
    numbers_in_head = [1 if NUMBER_RE.search(s["text"][:30]) else 0 for s in top]

    # 好反応の時間帯（上位群で頻度の高い時間帯 top3）
    hours = [s["hour"] for s in top if s["hour"] is not None]
    best_hours: list[int] = []
    if hours:
        from collections import Counter

        best_hours = [h for h, _ in Counter(hours).most_common(3)]

    profile = PatternProfile(
        platform=platform,
        sample_size=n,
        source="learned",
        top_avg_len=statistics.mean(top_lens) if top_lens else 0.0,
        all_avg_len=statistics.mean(all_lens) if all_lens else 0.0,
        best_hooks=_infer_hooks(top),
        best_hours=best_hours,
        hashtag_usage=statistics.mean(hashtag_counts) if hashtag_counts else 0.0,
        uses_numbers_ratio=(sum(numbers_in_head) / len(numbers_in_head)) if numbers_in_head else 0.0,
        top_examples=[s["text"][:40].replace("\n", " ") for s in top[:3]],
    )
    return profile


def _infer_hooks(top: list[dict]) -> list[str]:
    """上位投稿の1文目から、当てはまるフックの型を推定。"""
    found: set[str] = set()
    for s in top:
        head = s["text"].split("\n", 1)[0]
        if NUMBER_RE.search(head):
            found.add("数字を冒頭に置く（例: 3つの理由 / 月5万）")
        if any(w in head for w in ["やめ", "捨て", "不要", "間違"]):
            found.add("常識への逆張り（例: 〜はもうやめよう）")
        if any(w in head for w in ["ませんか", "ますか", "?", "？", "悩"]):
            found.add("読者の悩みへの直接呼びかけ（例: 〜で悩んでいませんか?）")
        if any(w in head for w in ["結論", "実は", "断言"]):
            found.add("結論ファースト（例: 結論から言うと〜）")
        if any(w in head for w in ["失敗", "溶か", "後悔", "学んだ"]):
            found.add("実体験・失敗談の告白（例: 100万溶かして学んだ）")
        if any(w in head for w in ["損", "限定", "知らないと", "今だけ"]):
            found.add("限定・希少性（例: 知らないと損する）")
    # 何も検出できなければ既定を返す
    return sorted(found) if found else DEFAULT_HOOKS[:3]


def merge_profiles(learned: PatternProfile, fallback: PatternProfile) -> PatternProfile:
    """学習結果と既定知識をハイブリッド統合（不足を既定で補う）。"""
    merged = PatternProfile(
        platform=learned.platform,
        sample_size=learned.sample_size,
        source="hybrid",
        top_avg_len=learned.top_avg_len,
        all_avg_len=learned.all_avg_len,
        best_hooks=learned.best_hooks or fallback.best_hooks,
        best_hours=learned.best_hours or fallback.best_hours,
        hashtag_usage=learned.hashtag_usage or fallback.hashtag_usage,
        uses_numbers_ratio=learned.uses_numbers_ratio or fallback.uses_numbers_ratio,
        top_examples=learned.top_examples,
        notes=fallback.notes,
    )
    return merged


def save_profiles(profiles: dict[str, PatternProfile], path: Path = PATTERNS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {k: asdict(v) for k, v in profiles.items()}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_profiles(path: Path = PATTERNS_PATH) -> dict[str, PatternProfile]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: PatternProfile(**v) for k, v in data.items()}


def get_profile(platform: str) -> PatternProfile:
    """保存済みプロファイルを取得。無ければ既定を返す。"""
    profiles = load_profiles()
    return profiles.get(platform) or default_profile(platform)
