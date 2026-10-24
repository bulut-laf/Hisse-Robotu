from __future__ import annotations

from types import SimpleNamespace

from app.analysis.intraday_candidate_validation import (
    validate_intraday_candidate,
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


def _freshness(*, state: str = "DATA_GUNCEL"):
    return SimpleNamespace(state=state)


def test_positive_continuous_with_supporting_volume():
    result = validate_intraday_candidate(_evidence(), _freshness())
    assert result.state == "ADAY_DESTEKLENIYOR"


def test_recovering_with_supporting_volume():
    result = validate_intraday_candidate(
        _evidence(movement_structure="TOPARLANIYOR"),
        _freshness(),
    )
    assert result.state == "ADAY_DESTEKLENIYOR"


def test_negative_continuous_is_not_supported():
    result = validate_intraday_candidate(
        _evidence(movement_structure="NEGATIF_SUREKLI"),
        _freshness(),
    )
    assert result.state == "ADAY_DESTEKLENMIYOR"


def test_weak_recovery_is_not_supported():
    result = validate_intraday_candidate(
        _evidence(movement_structure="TOPARLANMA_ZAYIF"),
        _freshness(),
    )
    assert result.state == "ADAY_DESTEKLENMIYOR"


def test_neutral_is_not_supported():
    result = validate_intraday_candidate(
        _evidence(movement_structure="NOTR"),
        _freshness(),
    )
    assert result.state == "ADAY_DESTEKLENMIYOR"


def test_delayed_data_is_insufficient():
    result = validate_intraday_candidate(
        _evidence(),
        _freshness(state="DATA_GECIKMELI"),
    )
    assert result.state == "VERI_YETERSIZ"


def test_insufficient_data_is_insufficient():
    result = validate_intraday_candidate(
        _evidence(),
        _freshness(state="DATA_YETERSIZ"),
    )
    assert result.state == "VERI_YETERSIZ"


def test_locked_data_is_insufficient():
    result = validate_intraday_candidate(
        _evidence(),
        _freshness(state="DATA_KILITLI"),
    )
    assert result.state == "VERI_YETERSIZ"

def test_preview_intraday_data_can_validate_candidate():
    evidence = _evidence()

    freshness = SimpleNamespace(
        state="DATA_GECIKMELI",
        preview_only=True,
        measured_delay_minutes=25.0,
    )

    result = validate_intraday_candidate(
        evidence,
        freshness,
    )

    assert result.state == "ADAY_DESTEKLENIYOR"
