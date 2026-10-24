from pathlib import Path


def test_engine_esik_politikasini_asama_motoruna_aktarir():
    source = Path("backend/app/prebreakout/prebreakout_engine.py").read_text(encoding="utf-8")
    assert "threshold_policy: PreBreakoutThresholdPolicy | None = None" in source
    assert "threshold_policy=threshold_policy" in source


def test_asama_motoru_varsayilan_esigi_geriye_donuk_korur():
    source = Path("backend/app/prebreakout/prebreakout_stage.py").read_text(encoding="utf-8")
    assert "threshold_policy or mevcut_esik_politikasi()" in source
    assert "minimum_momentum_score(required_stage)" in source
