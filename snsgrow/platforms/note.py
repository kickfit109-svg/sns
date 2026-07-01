"""note 用アダプタ。

note には公式の投稿APIが提供されていないため、自動投稿は行わず、
コピペしやすい Markdown 下書きを out/ に出力する。
"""
from __future__ import annotations

from pathlib import Path

from ..config import OUT_DIR
from ..core.generator import Draft
from .base import BasePoster, PostResult


class NotePoster(BasePoster):
    platform = "note"

    def available(self) -> bool:
        # note は公式投稿APIが無いため常に下書きモード
        return False

    def post(self, draft: Draft) -> PostResult:
        return self.save_draft(draft)

    def save_draft(self, draft: Draft) -> PostResult:
        OUT_DIR.mkdir(exist_ok=True)
        safe_topic = "".join(c for c in draft.topic if c.isalnum() or c in " 　_-")[:20].strip()
        path = OUT_DIR / f"note_{safe_topic or 'draft'}.md"

        lines = []
        if draft.title:
            lines.append(f"# {draft.title}\n")
        lines.extend(draft.parts)
        if draft.hashtags:
            lines.append("\n" + " ".join(draft.hashtags))
        path.write_text("\n".join(lines), encoding="utf-8")

        return PostResult(
            platform=self.platform,
            success=True,
            mode="draft",
            url=str(path),
            message=(
                f"noteは公式投稿APIが無いため下書きを出力しました: {path}\n"
                "  → note.com を開き、内容をコピペして投稿してください。"
            ),
        )
