import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snsgrow.core import analyzer  # noqa: E402


SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_posts.csv"


def test_learn_from_csv_extracts_pattern():
    profile = analyzer.learn_from_csv(SAMPLE, "x")
    assert profile.source == "learned"
    assert profile.sample_size == 10
    # 伸びた投稿の方が平均的に長い（雑談は短くスコアも低い想定）
    assert profile.top_avg_len > 0
    assert profile.best_hooks  # 何らかのフックを検出
    # 好反応時間帯が抽出されている
    assert profile.best_hours


def test_default_profile():
    profile = analyzer.default_profile("threads")
    assert profile.source == "default"
    assert profile.best_hooks
    assert "threads" == profile.platform


def test_merge_profiles_fills_gaps():
    learned = analyzer.PatternProfile(platform="x", sample_size=5, source="learned")
    fallback = analyzer.default_profile("x")
    merged = analyzer.merge_profiles(learned, fallback)
    assert merged.source == "hybrid"
    # 学習側が空だったフックが既定で補完される
    assert merged.best_hooks == fallback.best_hooks


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "patterns.json"
    profiles = {"x": analyzer.default_profile("x")}
    analyzer.save_profiles(profiles, path)
    loaded = analyzer.load_profiles(path)
    assert "x" in loaded
    assert loaded["x"].best_hooks == profiles["x"].best_hooks


def test_missing_text_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("foo,bar\n1,2\n", encoding="utf-8")
    try:
        analyzer.learn_from_csv(bad, "x")
        assert False, "例外が発生するべき"
    except ValueError:
        pass
