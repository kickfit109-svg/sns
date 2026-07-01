import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snsgrow.core import generator  # noqa: E402
from snsgrow.core.analyzer import default_profile  # noqa: E402


def test_offline_draft_x(monkeypatch):
    # APIキー無しでもオフライン下書きが返る
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    draft = generator.generate_draft("副業で月5万", "x", profile=default_profile("x"))
    assert draft.platform == "x"
    assert draft.parts
    assert draft.model == "offline-template"


def test_offline_draft_note(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    draft = generator.generate_draft("朝活のコツ", "note", profile=default_profile("note"))
    assert draft.platform == "note"
    assert draft.title  # note はタイトルを持つ
    assert draft.parts


def test_extract_json_from_fenced():
    text = '```json\n{"parts": ["hello"], "hashtags": ["#a"]}\n```'
    data = generator._extract_json(text)
    assert data["parts"] == ["hello"]


def test_extract_json_bare():
    text = 'ここに説明 {"parts": ["x"], "hashtags": []} 末尾'
    data = generator._extract_json(text)
    assert data["parts"] == ["x"]


def test_generate_all_covers_platforms(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    drafts = generator.generate_all("テスト", ["x", "threads", "note"])
    assert set(drafts.keys()) == {"x", "threads", "note"}
