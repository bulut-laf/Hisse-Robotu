from dataclasses import dataclass

from backend.app.analysis.high_conviction_buy_gate import (
    HIGH_CONFIDENCE,
    NORMAL_CONFIDENCE,
    WAIT,
    build_high_conviction_buy_gate,
    evaluate_historical_support,
)


@dataclass
class Card:
    symbol: str
    selection_source: str = "TARAMA"
    jump_quality: str = "-"
    entry_readiness: str = "-"


@dataclass
class Decision:
    priority: int = 1
    symbol: str = "AAA"
    decision: str = "AL"
    technical_score: int = 84
    technical_view: str = "Pozitif Teknik Görünüm"
    rank_change: int | None = 8
    research_priority: str = "HIGH"
    visibility_state: str | None = "IMPROVING"
    volume_ratio: float = 1.45
    risk_reward: float = 2.3
    data_status: str = "UYGUN"


@dataclass
class Slice:
    dimension: str
    segment: str
    horizon: str
    sample_size: int = 12
    hit_rate: float | None = 66.7
    average_return: float | None = 1.4
    status: str = "DESTEKLEYİCİ"


def supportive_history():
    return (
        Slice("Teknik skor", "80+", "3S"),
        Slice("Hacim", ">=1.3", "5S"),
        Slice("Risk/Getiri", ">=2", "3S"),
    )


def test_high_confidence_requires_all_strict_gates_and_history():
    result = build_high_conviction_buy_gate(
        (Card("AAA"),),
        (Decision(),),
        calibration_slices=supportive_history(),
    )[0]
    assert result.conviction == HIGH_CONFIDENCE
    assert not result.blockers


def test_al_without_history_remains_normal_confidence():
    result = build_high_conviction_buy_gate((Card("AAA"),), (Decision(),))[0]
    assert result.conviction == NORMAL_CONFIDENCE
    assert "Outcome geçmişi" in " ".join(result.blockers)


def test_base_wait_can_never_be_upgraded_to_buy():
    result = build_high_conviction_buy_gate(
        (Card("AAA"),),
        (Decision(decision="BEKLE"),),
        calibration_slices=supportive_history(),
    )[0]
    assert result.conviction == WAIT


def test_jump_candidate_requires_quality_and_entry_readiness():
    card = Card("AAA", selection_source="SICRAMA", jump_quality="UYGUN", entry_readiness="TEYİT BEKLİYOR")
    result = build_high_conviction_buy_gate(
        (card,),
        (Decision(),),
        calibration_slices=supportive_history(),
    )[0]
    assert result.conviction == NORMAL_CONFIDENCE
    assert result.entry_gate == "KALDI"


def test_history_support_uses_existing_calibration_not_new_score():
    support = evaluate_historical_support(Decision(), supportive_history())
    assert support.status == "DESTEKLEYİCİ"
    assert support.supportive_slices == 3
