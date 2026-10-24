from __future__ import annotations

from types import SimpleNamespace

from app.analysis.eod_decision_gate import (
    evaluate_eod_decision,
)


def _validation(state: str = "ADAY_DESTEKLENIYOR"):
    return SimpleNamespace(state=state)


def _freshness(state: str = "DATA_GUNCEL"):
    return SimpleNamespace(
        state=state,
        preview_only=False,
    )


def _evidence(
    *,
    movement_structure: str = "POZITIF_SUREKLI",
    volume_state: str = "DESTEKLIYOR",
):
    return SimpleNamespace(
        movement_structure=movement_structure,
        volume_state=volume_state,
    )


def _close(
    *,
    close_state: str = "POZITIF_KAPANIS",
):
    return SimpleNamespace(
        close_state=close_state,
    )


def test_supported_candidate_with_positive_close_is_buy_candidate():
    result = evaluate_eod_decision(
        _validation(),
        _freshness(),
        _evidence(),
        _close(),
    )

    assert result.state == "ALIS_ADAYI"


def test_supported_candidate_with_weak_close_waits():
    result = evaluate_eod_decision(
        _validation(),
        _freshness(),
        _evidence(),
        _close(close_state="ZAYIF_KAPANIS"),
    )

    assert result.state == "BEKLE"


def test_supported_candidate_with_negative_close_is_eliminated():
    result = evaluate_eod_decision(
        _validation(),
        _freshness(),
        _evidence(),
        _close(close_state="NEGATIF_KAPANIS"),
    )

    assert result.state == "ELENDI"


def test_not_supported_candidate_is_eliminated():
    result = evaluate_eod_decision(
        _validation("ADAY_DESTEKLENMIYOR"),
        _freshness(),
        _evidence(),
        _close(),
    )

    assert result.state == "ELENDI"


def test_insufficient_validation_is_wait():
    result = evaluate_eod_decision(
        _validation("VERI_YETERSIZ"),
        _freshness(),
        _evidence(),
        _close(),
    )

    assert result.state == "BEKLE"


def test_locked_data_is_wait():
    result = evaluate_eod_decision(
        _validation(),
        _freshness("DATA_KILITLI"),
        _evidence(),
        _close(),
    )

    assert result.state == "BEKLE"


def test_insufficient_data_is_wait():
    result = evaluate_eod_decision(
        _validation(),
        _freshness("DATA_YETERSIZ"),
        _evidence(),
        _close(),
    )

    assert result.state == "BEKLE"


def test_positive_close_without_supporting_volume_waits():
    result = evaluate_eod_decision(
        _validation(),
        _freshness(),
        _evidence(volume_state="ZAYIF"),
        _close(),
    )

    assert result.state == "BEKLE"
