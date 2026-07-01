"""環境変数・設定の読み込み。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv 未インストールでも動く
    pass


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "out"
PATTERNS_PATH = DATA_DIR / "patterns.json"

DEFAULT_MODEL = os.environ.get("SNSGROW_MODEL", "claude-sonnet-5")

# 各プラットフォームの制約
PLATFORM_LIMITS = {
    "x": {"max_chars": 280, "supports_thread": True, "supports_image": True},
    "threads": {"max_chars": 500, "supports_thread": True, "supports_image": True},
    "note": {"max_chars": 0, "supports_thread": False, "supports_image": True},  # 0 = 実質無制限
}

PLATFORMS = ("x", "threads", "note")


@dataclass
class XCreds:
    api_key: str | None
    api_secret: str | None
    access_token: str | None
    access_secret: str | None

    @property
    def is_complete(self) -> bool:
        return all([self.api_key, self.api_secret, self.access_token, self.access_secret])


@dataclass
class ThreadsCreds:
    access_token: str | None
    user_id: str | None

    @property
    def is_complete(self) -> bool:
        return all([self.access_token, self.user_id])


def get_anthropic_key() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY") or None


def get_x_creds() -> XCreds:
    return XCreds(
        api_key=os.environ.get("X_API_KEY") or None,
        api_secret=os.environ.get("X_API_SECRET") or None,
        access_token=os.environ.get("X_ACCESS_TOKEN") or None,
        access_secret=os.environ.get("X_ACCESS_SECRET") or None,
    )


def get_threads_creds() -> ThreadsCreds:
    return ThreadsCreds(
        access_token=os.environ.get("THREADS_ACCESS_TOKEN") or None,
        user_id=os.environ.get("THREADS_USER_ID") or None,
    )


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(exist_ok=True)
