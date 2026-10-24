import pytest

from backend.app.prebreakout.prebreakout_early_radar import (
    EarlyRadarDecision,
    EarlyRadarInput,
    MaturityDecision,
    as_display_dict,
    classify_early_radar,
)


def make(**overrides):
    data = dict(
        rank=18,
        stage="E1",
        momentum=60,
        rank_velocity=4,
        score_velocity=3,
        momentum_velocity=2,
        sessions_since_first_seen=3,
        realized_move_pct=6,
        score=65,
        resistance_distance_pct=5,
    )
    data.update(overrides)
    return EarlyRadarInput(**data)


def test_11_20_erken_asama_yuksek_oncelik():
    out = classify_early_radar(make())
    assert out.early_radar is EarlyRadarDecision.YUKSEK_ONCELIK
    assert out.maturity is MaturityDecision.NORMAL
    assert out.movement_phase == "ERKEN / GELİŞİYOR"


def test_21_30_erken_asama_ivme_ile_yuksek_oncelik():
    out = classify_early_radar(make(rank=24, stage="E0", rank_velocity=5))
    assert out.early_radar is EarlyRadarDecision.YUKSEK_ONCELIK


def test_ilk5_uzun_hareket_kar_koruma():
    out = classify_early_radar(
        make(
            rank=3,
            stage="B",
            sessions_since_first_seen=8,
            realized_move_pct=24,
            rank_velocity=1,
            score_velocity=0,
            momentum_velocity=-1,
        )
    )
    assert out.maturity is MaturityDecision.KAR_KORUMA
    assert out.early_radar is EarlyRadarDecision.YOK
    assert out.movement_phase == "OLGUN"


def test_ilk5_hizli_geldiyse_sadece_olgunlasiyor():
    out = classify_early_radar(
        make(
            rank=4,
            stage="B",
            sessions_since_first_seen=2,
            realized_move_pct=7,
        )
    )
    assert out.maturity is MaturityDecision.OLGUNLASIYOR
    assert out.early_radar is not EarlyRadarDecision.YUKSEK_ONCELIK


def test_prim_yuksekse_erken_firsat_puani_duser():
    early = classify_early_radar(make(realized_move_pct=5))
    late = classify_early_radar(make(realized_move_pct=26))
    assert late.priority_score < early.priority_score


def test_hareket_yasi_yuksekse_puan_duser():
    young = classify_early_radar(make(sessions_since_first_seen=2))
    old = classify_early_radar(make(sessions_since_first_seen=9))
    assert old.priority_score < young.priority_score


def test_rank_ivmesi_puani_artirir():
    flat = classify_early_radar(make(rank_velocity=0))
    rising = classify_early_radar(make(rank_velocity=5))
    assert rising.priority_score > flat.priority_score


def test_e0_e1_e2_erken_asama_bonus():
    e1 = classify_early_radar(make(stage="E1"))
    b = classify_early_radar(make(stage="B"))
    assert e1.priority_score > b.priority_score


def test_display_dict_ui_icin_hazir():
    out = classify_early_radar(make())
    view = as_display_dict(out)
    assert view["Erken Radar"] == "Yüksek Öncelik"
    assert "Erken Fırsat Puanı" in view
    assert "Hareket Fazı" in view
    assert "Olgunlaşma" in view


def test_gecersiz_rank_reddedilir():
    with pytest.raises(ValueError):
        make(rank=0)


def test_gecersiz_score_reddedilir():
    with pytest.raises(ValueError):
        make(score=101)


def test_negatif_seans_reddedilir():
    with pytest.raises(ValueError):
        make(sessions_since_first_seen=-1)


def test_esik_sirasi_gecersizse_hata():
    with pytest.raises(ValueError):
        classify_early_radar(make(), high_priority_threshold=40, watch_threshold=50)


def test_maturity_esikleri_gecersizse_hata():
    with pytest.raises(ValueError):
        classify_early_radar(make(), maturity_sessions=0)
    with pytest.raises(ValueError):
        classify_early_radar(make(), maturity_move_pct=0)


def test_ilk5_ve_yuksek_getiri_yeni_giris_mesaji_gec():
    out = classify_early_radar(
        make(rank=2, realized_move_pct=28, sessions_since_first_seen=7)
    )
    assert "geç olabilir" in out.new_entry_message.lower()
    assert "kâr koruma" in out.position_message.lower()
