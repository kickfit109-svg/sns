"""投稿アダプタの共通インターフェース。"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.generator import Draft


@dataclass
class PostResult:
    platform: str
    success: bool
    mode: str  # "posted" | "draft" | "error"
    url: str | None = None
    message: str = ""


class BasePoster:
    platform: str = "base"

    def available(self) -> bool:
        """自動投稿が可能か（APIキー等が揃っているか）。"""
        return False

    def post(self, draft: Draft) -> PostResult:  # pragma: no cover - 抽象
        raise NotImplementedError

    def save_draft(self, draft: Draft) -> PostResult:
        """下書きとして扱う（実投稿しない）。"""
        return PostResult(
            platform=self.platform,
            success=True,
            mode="draft",
            message="下書きとして保存しました（自動投稿は行っていません）。",
        )
