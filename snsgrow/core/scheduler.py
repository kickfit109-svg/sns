"""投稿タイミングの提案。

学習済みプロファイルの好反応時間帯から、次の最適投稿時刻を算出する。
実際の予約投稿は cron や OS のスケジューラと組み合わせて使う想定。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .analyzer import get_profile


def next_optimal_time(platform: str, now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    profile = get_profile(platform)
    hours = sorted(profile.best_hours) or [7, 12, 21]

    # 今日の残りの好反応時間帯で最も近いもの
    for h in hours:
        candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if candidate > now:
            return candidate
    # 今日分が過ぎていれば翌日の最初の時間帯
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=hours[0], minute=0, second=0, microsecond=0)


def cron_hint(platform: str) -> str:
    profile = get_profile(platform)
    hours = sorted(profile.best_hours) or [7, 12, 21]
    hour_field = ",".join(str(h) for h in hours)
    return f"0 {hour_field} * * *  # {platform} の好反応時間帯に定期実行"
