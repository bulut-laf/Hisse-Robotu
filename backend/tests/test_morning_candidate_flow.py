from types import SimpleNamespace

from backend.app.analysis.morning_candidate_flow import (
    build_morning_candidate_cards,
    morning_candidate_rows,
)


def _candidate(symbol, score, view, volume=1.5, rr=2.0):
    return SimpleNamespace(
        sembol=symbol,
        hacim_orani=volume,
        sinyal=SimpleNamespace(
            skor=score,
            karar=view,
            pozitif_nedenler=("Momentum güçlü.", "Hacim destekliyor."),
            riskler=("Stop disiplini gerekli.",),
        ),
        risk_plani=SimpleNamespace(
            risk_odul_orani=rr,
        ),
    )


def _visibility(symbol, priority, change, blocked=False):
    return SimpleNamespace(
        symbol=symbol,
        research_priority=priority,
        visibility_state="IMPROVING",
        rank_change=change,
        data_blocked=blocked,
    )


def test_morning_candidate_flow_preserves_existing_scan_order_and_limits_to_five():
    scan_result = SimpleNamespace(
        adaylar=tuple(
            _candidate(f"S{i}.IS", 100 - i, "Pozitif Teknik Görünüm")
            for i in range(1, 8)
        )
    )

    cards = build_morning_candidate_cards(scan_result, limit=5)

    assert [item.symbol for item in cards] == ["S1", "S2", "S3", "S4", "S5"]
    assert [item.rank for item in cards] == [1, 2, 3, 4, 5]


def test_morning_candidate_flow_attaches_early_visibility_without_new_score():
    scan_result = SimpleNamespace(
        adaylar=(
            _candidate("TUPRS.IS", 82, "Pozitif Teknik Görünüm", 1.8, 2.4),
        )
    )

    cards = build_morning_candidate_cards(
        scan_result,
        visibility_contexts=(
            _visibility("TUPRS", "HIGH", 34),
        ),
    )

    card = cards[0]
    assert card.symbol == "TUPRS"
    assert card.technical_score == 82
    assert card.research_priority == "HIGH"
    assert card.rank_change == 34
    assert card.operational_status == "ARAŞTIRMA ÖNCELİĞİ YÜKSEK"


def test_morning_candidate_flow_marks_data_blocked_candidate():
    scan_result = SimpleNamespace(
        adaylar=(
            _candidate("AAA.IS", 79, "Pozitif Teknik Görünüm"),
        )
    )

    cards = build_morning_candidate_cards(
        scan_result,
        visibility_contexts=(
            _visibility("AAA", "HIGH", 25, blocked=True),
        ),
    )

    assert cards[0].data_blocked is True
    assert cards[0].operational_status == "KISMİ VERİ — İNCELEMEYE DEVAM"


def test_morning_candidate_rows_exposes_decision_card_fields():
    scan_result = SimpleNamespace(
        adaylar=(
            _candidate("TUPRS.IS", 82, "Pozitif Teknik Görünüm", 1.8, 2.4),
        )
    )
    cards = build_morning_candidate_cards(scan_result)
    rows = morning_candidate_rows(cards)

    assert rows[0]["Hisse"] == "TUPRS"
    assert rows[0]["Skor"] == 82
    assert rows[0]["Hacim oranı"] == 1.8
    assert rows[0]["Risk/Getiri"] == 2.4
    assert "Momentum güçlü." in rows[0]["Nedenler"]
    assert "Stop disiplini gerekli." in rows[0]["Riskler"]
