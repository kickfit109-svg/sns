"""X (旧Twitter) への自動投稿。API v2 + OAuth1.0a を使用。

複数パートはスレッド（返信チェーン）として連続投稿する。
requests-oauthlib のみに依存（tweepy不要）。
"""
from __future__ import annotations

from ..config import get_x_creds
from ..core.generator import Draft
from .base import BasePoster, PostResult

TWEET_URL = "https://api.twitter.com/2/tweets"


class XPoster(BasePoster):
    platform = "x"

    def __init__(self) -> None:
        self.creds = get_x_creds()

    def available(self) -> bool:
        return self.creds.is_complete

    def _session(self):
        from requests_oauthlib import OAuth1Session

        return OAuth1Session(
            client_key=self.creds.api_key,
            client_secret=self.creds.api_secret,
            resource_owner_key=self.creds.access_token,
            resource_owner_secret=self.creds.access_secret,
        )

    def post(self, draft: Draft) -> PostResult:
        if not self.available():
            return PostResult(
                platform=self.platform,
                success=False,
                mode="draft",
                message="X APIキーが未設定のため下書きモードです。.env を設定すると自動投稿できます。",
            )

        session = self._session()
        reply_to: str | None = None
        first_id: str | None = None

        parts = self._compose_parts(draft)
        for i, text in enumerate(parts):
            payload: dict = {"text": text}
            if reply_to:
                payload["reply"] = {"in_reply_to_tweet_id": reply_to}
            try:
                resp = session.post(TWEET_URL, json=payload, timeout=30)
            except Exception as e:
                return PostResult(self.platform, False, "error", message=f"通信エラー: {e}")

            if resp.status_code not in (200, 201):
                return PostResult(
                    self.platform,
                    False,
                    "error",
                    message=f"投稿失敗 (HTTP {resp.status_code}): {resp.text[:200]}",
                )
            tweet_id = resp.json().get("data", {}).get("id")
            reply_to = tweet_id
            if first_id is None:
                first_id = tweet_id

        url = f"https://x.com/i/status/{first_id}" if first_id else None
        return PostResult(
            self.platform, True, "posted", url=url,
            message=f"{len(parts)}件の投稿に成功しました。",
        )

    def _compose_parts(self, draft: Draft) -> list[str]:
        """パートを280文字制限に収まるよう調整し、末尾投稿にハッシュタグを付与。"""
        parts = list(draft.parts) or [draft.topic]
        if draft.hashtags:
            tag_line = " ".join(draft.hashtags)
            if len(parts[-1]) + len(tag_line) + 2 <= 280:
                parts[-1] = parts[-1] + "\n\n" + tag_line
            else:
                parts.append(tag_line)
        # 各パートが280超過なら安全のため切り詰め（本来は生成側で分割済み想定）
        return [p if len(p) <= 280 else p[:277] + "…" for p in parts]
