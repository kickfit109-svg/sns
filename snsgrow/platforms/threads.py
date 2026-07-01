"""Threads への自動投稿。Threads Graph API を使用。

投稿は2段階: (1) メディアコンテナ作成 → (2) publish。
複数パートは最初の投稿への返信チェーンで擬似スレッド化する。
"""
from __future__ import annotations

import requests

from ..config import get_threads_creds
from ..core.generator import Draft
from .base import BasePoster, PostResult

GRAPH_BASE = "https://graph.threads.net/v1.0"


class ThreadsPoster(BasePoster):
    platform = "threads"

    def __init__(self) -> None:
        self.creds = get_threads_creds()

    def available(self) -> bool:
        return self.creds.is_complete

    def post(self, draft: Draft) -> PostResult:
        if not self.available():
            return PostResult(
                platform=self.platform,
                success=False,
                mode="draft",
                message="Threads APIトークンが未設定のため下書きモードです。.env を設定すると自動投稿できます。",
            )

        parts = self._compose_parts(draft)
        reply_to: str | None = None
        first_id: str | None = None

        for text in parts:
            try:
                media_id = self._create_container(text, reply_to)
                published_id = self._publish(media_id)
            except Exception as e:
                return PostResult(self.platform, False, "error", message=f"投稿失敗: {e}")
            reply_to = published_id
            if first_id is None:
                first_id = published_id

        return PostResult(
            self.platform, True, "posted",
            url=None,
            message=f"{len(parts)}件の投稿に成功しました (先頭ID: {first_id})。",
        )

    def _create_container(self, text: str, reply_to: str | None) -> str:
        params = {
            "media_type": "TEXT",
            "text": text,
            "access_token": self.creds.access_token,
        }
        if reply_to:
            params["reply_to_id"] = reply_to
        r = requests.post(f"{GRAPH_BASE}/{self.creds.user_id}/threads", params=params, timeout=30)
        r.raise_for_status()
        return r.json()["id"]

    def _publish(self, creation_id: str) -> str:
        params = {"creation_id": creation_id, "access_token": self.creds.access_token}
        r = requests.post(
            f"{GRAPH_BASE}/{self.creds.user_id}/threads_publish", params=params, timeout=30
        )
        r.raise_for_status()
        return r.json()["id"]

    def _compose_parts(self, draft: Draft) -> list[str]:
        parts = list(draft.parts) or [draft.topic]
        if draft.hashtags:
            tag_line = " ".join(draft.hashtags)
            parts[-1] = parts[-1] + "\n\n" + tag_line
        return [p if len(p) <= 500 else p[:497] + "…" for p in parts]
