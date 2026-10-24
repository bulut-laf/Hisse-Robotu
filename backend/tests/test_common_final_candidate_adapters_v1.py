from types import SimpleNamespace

import pandas as pd
import pytest

from backend.app.analysis.common_final_candidate_adapters_v1 import (
    adapt_morning_candidate_cards,
    adapt_opportunity_radar_result,
    adapt_weekly_opportunity_candidates,
    build_common_final_candidates,
)


def test_morning_adapter_preserves_rank_and_maps_jump_source():
    cards = [
        SimpleNamespace(
            rank=2, symbol="abc.is", selection_source="SICRAMA",
            technical_score=81, volume_ratio=1.4, risk_reward=2.1,
            entry_readiness="GİRİŞE HAZIR", operational_status="TEKNİK ADAY",
            data_blocked=False, selection_reason="Sıçrama", positive_reasons=("Hacim",),
            risks=(), priority_reason="Öncelik", jump_quality_reason="Kalite",
            entry_readiness_reason="Teyit",
        ),
        SimpleNamespace(
            rank=1, symbol="XYZ", selection_source="TARAMA",
            technical_score=75, volume_ratio=1.1, risk_reward=1.7,
            entry_readiness="TEYİT BEKLİYOR", operational_status="TEYİT BEKLİYOR",
            data_blocked=True, selection_reason="Tarama", positive_reasons=(), risks=(),
        ),
    ]
    rows = adapt_morning_candidate_cards(cards)
    assert [x["symbol"] for x in rows] == ["ABC", "XYZ"]
    assert rows[0]["source"] == "SICRAMA"
    assert rows[0]["priority"] == 40002
    assert rows[1]["data_status"] == "ENGELLI"


def test_weekly_adapter_does_not_promote_stage_to_technical_score():
    candidate = SimpleNamespace(
        symbol="abc.is", stage=SimpleNamespace(value="W4_HIGH_CONVICTION_ACTIVATION_WATCH"),
        state=SimpleNamespace(value="CLEAN"), research_rank=3,
        why_visible_now="Yapı gelişiyor", what_must_happen_next="Hacim teyidi",
        what_invalidates_setup="Yapı bozulması", soft_contradictions=(),
        pilot_research_status="PILOT_SHORTLIST", next_day_status="WATCH",
        price_plan=SimpleNamespace(risk_reward=2.2),
    )
    rows = adapt_weekly_opportunity_candidates(SimpleNamespace(candidates=(candidate,)))
    assert len(rows) == 1
    assert rows[0]["symbol"] == "ABC"
    assert rows[0]["technical_score"] is None
    assert rows[0]["risk_reward"] == 2.2
    assert "W4_HIGH_CONVICTION_ACTIVATION_WATCH" in rows[0]["status"]
    assert rows[0]["data_status"] == ""


def test_opportunity_radar_keeps_weekly_and_monthly_scores_source_specific():
    radar = SimpleNamespace(
        weekly=pd.DataFrame([{
            "Hisse": "abc", "Validated Öncelik": 1, "Durum": "Validated",
            "Weekly Score": 77, "Validated Quality": 0.8, "Validated Profile Count": 4,
        }]),
        monthly_strong=pd.DataFrame([{
            "Hisse": "def", "Aylık Sınıf": "Güçlü Trend", "Aylık Skor": 83,
            "Durum": "Validated", "Neden seçildi?": "Güçlü göreli performans",
        }]),
        monthly_early=pd.DataFrame([{
            "Hisse": "ghi", "Aylık Sınıf": "Erken Dönüş", "Aylık Skor": 61,
            "Durum": "Henüz Validate Değil", "Neden seçildi?": "Higher-low",
        }]),
    )
    rows = adapt_opportunity_radar_result(radar)
    assert [x["symbol"] for x in rows] == ["ABC", "DEF", "GHI"]
    assert all(x["technical_score"] is None for x in rows)
    assert rows[0]["priority"] == 20001
    assert rows[1]["source"] == "FIRSAT_RADARI_AYLIK"
    assert "Aylık Skor=83" in rows[1]["reason"]
    assert "Güçlü Trend" in rows[1]["reason"]
    assert rows[0]["data_status"] == ""
    assert rows[1]["data_status"] == ""
    assert rows[2]["data_status"] == ""


def test_common_builder_merges_same_symbol_and_retains_source_evidence():
    morning = [SimpleNamespace(
        rank=1, symbol="abc", selection_source="TARAMA", technical_score=79,
        volume_ratio=1.2, risk_reward=1.8, entry_readiness="TEYİT BEKLİYOR",
        operational_status="TEKNİK ADAY", data_blocked=False,
        selection_reason="Teknik tarama", positive_reasons=(), risks=(),
    )]
    weekly = SimpleNamespace(candidates=(SimpleNamespace(
        symbol="ABC", stage="W3", state="CLEAN", research_rank=2,
        why_visible_now="Haftalık yapı", what_must_happen_next="Teyit",
        what_invalidates_setup="Yapı bozulması", soft_contradictions=(),
        pilot_research_status="REVIEW", next_day_status="WATCH",
        price_plan=SimpleNamespace(risk_reward=2.0),
    ),))
    output = build_common_final_candidates(morning_cards=morning, weekly_opportunities=weekly)
    assert len(output) == 1
    assert output[0].symbol == "ABC"
    assert set(output[0].sources) == {"TEKNIK_TARAMA", "FIRSAT_RADARI_HAFTALIK"}
    assert len(output[0].evidence) == 2
    assert output[0].technical_score == 79
    assert output[0].risk_reward == 2.0


def test_empty_inputs_return_empty_tuple():
    assert build_common_final_candidates() == ()


def test_limit_zero_returns_empty_and_negative_limit_is_rejected():
    cards = [SimpleNamespace(
        rank=1, symbol="ABC", selection_source="TARAMA", technical_score=50,
        volume_ratio=1, risk_reward=1, entry_readiness="-",
        operational_status="TEYİT", data_blocked=False, selection_reason="",
        positive_reasons=(), risks=(),
    )]
    assert build_common_final_candidates(morning_cards=cards, limit=0) == ()
    with pytest.raises(ValueError):
        build_common_final_candidates(morning_cards=cards, limit=-1)


def test_blank_symbols_are_ignored():
    assert adapt_morning_candidate_cards([SimpleNamespace(symbol=" ", rank=1)]) == ()


def test_radar_validation_status_is_not_data_availability():
    radar = SimpleNamespace(
        weekly=pd.DataFrame([{
            "Hisse": "ABC", "Validated Öncelik": 1, "Durum": "Validated",
            "Weekly Score": 70,
        }]),
        monthly_strong=pd.DataFrame([{
            "Hisse": "DEF", "Aylık Sınıf": "Güçlü Trend", "Aylık Skor": 82,
            "Durum": "Henüz Validate Değil",
        }]),
        monthly_early=pd.DataFrame(),
    )
    rows = adapt_opportunity_radar_result(radar)
    assert rows[0]["status"] == "Validated"
    assert rows[1]["status"] == "AYLIK_GUCLU | Henüz Validate Değil"
    assert all(row["data_status"] == "" for row in rows)
