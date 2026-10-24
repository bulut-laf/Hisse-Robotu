from pathlib import Path


def test_ranking_jump_ui_present_in_dashboard():
    root = Path(__file__).resolve().parents[2]
    text = (root / "backend" / "dashboard.py").read_text(encoding="utf-8")

    assert "RANKING_JUMP_V1_UI" in text
    assert "Sıralama Hareketi / Erken Görünürlük" in text
    assert "3S Erken Sıçrayanlar" in text
    assert "build_rank_trajectories" in text
    assert "RankObservationJsonlStore" in text
    assert "Bu görünüm AL/SAT kararı üretmez" in text


def test_ranking_jump_ui_is_bound_to_research_section():
    root = Path(__file__).resolve().parents[2]
    text = (root / "backend" / "dashboard.py").read_text(encoding="utf-8")

    seam = text.index("_three_all_rows = aday_tablosu_kayitlari(sonuc)")
    marker = text.index("RANKING_JUMP_V1_UI", seam)
    first_empty_guard = text.index("if not kayitlar:", seam)

    assert seam < marker < first_empty_guard


def test_ranking_jump_ui_has_no_trade_authority():
    root = Path(__file__).resolve().parents[2]
    text = (root / "backend" / "dashboard.py").read_text(encoding="utf-8")

    start = text.index("RANKING_JUMP_V1_UI")
    end = text.index("RANKING_JUMP_V1_UI_END", start)
    block = text[start:end]

    assert "_alsata_aday_gonder" not in block
    assert "robot_score" not in block
    assert "robot_decision" not in block
