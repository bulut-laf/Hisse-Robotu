from datetime import date

import pytest

from backend.app.news_center.daily_developments import build_daily_developments_brief


def test_onem_esigi_0_100_araliginda_olmalidir():
    with pytest.raises(ValueError, match="0-100"):
        build_daily_developments_brief((), {}, selected_date=date(2026, 8, 5), min_importance=101)


def test_yeni_gizli_puan_alani_yoktur():
    annotations = build_daily_developments_brief.__annotations__
    assert "ai_score" not in annotations
    assert "technical_score" not in annotations
    assert "daily_score" not in annotations
