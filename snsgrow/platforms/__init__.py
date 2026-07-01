"""各SNSへの投稿アダプタ。"""
from __future__ import annotations

from ..core.generator import Draft
from .base import PostResult
from .note import NotePoster
from .threads import ThreadsPoster
from .x import XPoster


def get_poster(platform: str):
    if platform == "x":
        return XPoster()
    if platform == "threads":
        return ThreadsPoster()
    if platform == "note":
        return NotePoster()
    raise ValueError(f"未知のプラットフォーム: {platform}")


__all__ = ["get_poster", "PostResult", "Draft"]
