import pytest

from backend.app.prebreakout.prebreakout_scan_radar_integration import (
    ScanCandidateSnapshot,
    build_radar_cards,
    build_radar_cards_from_rows,
    candidate_to_card,
    candidate_to_radar_input,
    snapshot_from_mapping,
)


def snap(**overrides):
    data = dict(
        symbol="TRMET",
        rank=18,
        stage="E1",
        momentum=60,
        score=65,
        resistance_distance_pct=5,
        sessions_since_first_seen=3,
        realized_move_pct=6,
        rank_velocity=4,
        score_velocity=3,
        momentum_velocity=2,
    )
    data.update(overrides)
    return ScanCandidateSnapshot(**data)


def test_candidate_to_radar_input():
    x = candidate_to_radar_input(snap())
    assert x.rank == 18
    assert x.stage == "E1"
    assert x.rank_velocity == 4


def test_candidate_to_card_erken_radar():
    card = candidate_to_card(snap())
    assert card.symbol == "TRMET"
    assert card.early_radar == "Yüksek Öncelik"
    assert card.movement_phase == "ERKEN / GELİŞİYOR"


def test_candidate_to_card_kar_koruma():
    card = candidate_to_card(
        snap(
            rank=3,
            stage="B",
            sessions_since_first_seen=8,
            realized_move_pct=25,
            rank_velocity=1,
            score_velocity=0,
            momentum_velocity=-1,
        )
    )
    assert card.maturity == "Kâr Koruma"
    assert card.early_radar == "Yok"


def test_build_radar_cards_sirayi_korur():
    cards = build_radar_cards(
        [
            snap(symbol="AAA"),
            snap(symbol="BBB", rank=24, stage="E0"),
        ]
    )
    assert [x.symbol for x in cards] == ["AAA", "BBB"]


def test_snapshot_from_turkce_mapping():
    row = {
        "Hisse": "TRMET",
        "Sıra": 18,
        "Kesim sınıfı": "E1",
        "Momentum": 60,
        "Teknik skor": 65,
        "Dirence uzaklık (%)": 5.2,
        "Hareket yaşı": 3,
        "Gerçekleşmiş hareket (%)": 6.5,
        "Sıra ivmesi": 4,
        "Skor ivmesi": 3,
        "Momentum ivmesi": 2,
    }
    x = snapshot_from_mapping(row)
    assert x.symbol == "TRMET"
    assert x.rank == 18
    assert x.resistance_distance_pct == pytest.approx(5.2)


def test_snapshot_from_sade_mapping():
    row = {
        "symbol": "AAA",
        "rank": 22,
        "stage": "E0",
        "momentum": 55,
        "score": 60,
        "sessions_since_first_seen": 2,
        "realized_move_pct": 4,
        "rank_velocity": 5,
        "score_velocity": 2,
        "momentum_velocity": 1,
    }
    x = snapshot_from_mapping(row)
    assert x.symbol == "AAA"
    assert x.rank == 22


def test_mapping_gecmis_metrikleri_eksikse_guvenli_varsayim():
    row = {
        "Hisse": "AAA",
        "Sıra": 20,
        "Kesim sınıfı": "E1",
        "Momentum": 58,
    }
    x = snapshot_from_mapping(row)
    assert x.sessions_since_first_seen == 0
    assert x.realized_move_pct == 0.0
    assert x.rank_velocity is None


def test_build_radar_cards_from_rows():
    rows = [
        {
            "Hisse": "AAA",
            "Sıra": 18,
            "Kesim sınıfı": "E1",
            "Momentum": 60,
            "Hareket yaşı": 3,
            "Gerçekleşmiş hareket (%)": 5,
            "Sıra ivmesi": 4,
            "Skor ivmesi": 2,
            "Momentum ivmesi": 2,
        }
    ]
    cards = build_radar_cards_from_rows(rows)
    assert len(cards) == 1
    assert cards[0].symbol == "AAA"
    assert cards[0].early_radar == "Yüksek Öncelik"


def test_bos_symbol_reddedilir():
    with pytest.raises(ValueError):
        snap(symbol=" ")


def test_gecersiz_rank_reddedilir():
    with pytest.raises(ValueError):
        snap(rank=0)


def test_gecersiz_score_reddedilir():
    with pytest.raises(ValueError):
        snap(score=101)


def test_negatif_hareket_yasi_reddedilir():
    with pytest.raises(ValueError):
        snap(sessions_since_first_seen=-1)


def test_mapping_symbol_yoksa_hata():
    with pytest.raises(ValueError):
        snapshot_from_mapping({"Sıra": 10})


def test_mapping_bos_opsiyoneller():
    row = {
        "Hisse": "AAA",
        "Sıra": "",
        "Kesim sınıfı": "",
        "Momentum": "",
        "Teknik skor": "",
        "Dirence uzaklık (%)": "",
    }
    x = snapshot_from_mapping(row)
    assert x.rank is None
    assert x.stage is None
    assert x.momentum is None
    assert x.score is None
    assert x.resistance_distance_pct is None
