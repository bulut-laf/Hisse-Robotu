from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

import app.analysis.financial_intelligence_bank_daily_production_bridge as bridge


def _record() -> dict:
    return {
        "source_type": "OFFICIAL_SOURCE_BUNDLE",
        "source_uri": "file:///tmp/GARAN_bundle.json",
        "symbol": "GARAN",
        "sector_model": "BANK",
        "period_end": "2026-06-30",
        "publication_date": "2026-07-30",
        "as_of": "2026-07-30",
        "canonical_facts": {},
        "evidence_hash": "sha256:" + ("a" * 64),
    }


def _onboarding_result(**overrides):
    values = {
        "status": "PASS",
        "symbol": "GARAN",
        "source_type": "OFFICIAL_SOURCE_BUNDLE",
        "source_uri": "file:///tmp/GARAN_bundle.json",
        "as_of": "2026-07-30",
        "publication_date": "2026-07-30",
        "canonical_input_ready": True,
        "scoring_ready": True,
        "production_evidence": True,
        "activation_ready": True,
        "blocker": None,
    }

    values.update(overrides)

    return SimpleNamespace(**values)


def test_activation_ready_source_builds_daily_context(
    monkeypatch,
):
    monkeypatch.setattr(
        bridge,
        "evaluate_bank_production_source",
        lambda record: _onboarding_result(),
    )

    result = bridge.build_bank_daily_production_context(
        _record()
    )

    assert result is not None
    assert result.symbol == "GARAN"
    assert result.as_of == "2026-07-30"
    assert result.publication_date == "2026-07-30"
    assert result.source_type == "OFFICIAL_SOURCE_BUNDLE"
    assert result.canonical_input_ready is True
    assert result.scoring_ready is True
    assert result.production_evidence is True
    assert result.activation_ready is True


@pytest.mark.parametrize(
    "field",
    (
        "canonical_input_ready",
        "scoring_ready",
        "production_evidence",
        "activation_ready",
    ),
)
def test_incomplete_state_fails_closed(
    monkeypatch,
    field,
):
    monkeypatch.setattr(
        bridge,
        "evaluate_bank_production_source",
        lambda record: _onboarding_result(
            **{field: False}
        ),
    )

    assert (
        bridge.build_bank_daily_production_context(
            _record()
        )
        is None
    )


def test_blocked_onboarding_fails_closed(
    monkeypatch,
):
    monkeypatch.setattr(
        bridge,
        "evaluate_bank_production_source",
        lambda record: _onboarding_result(
            status="BLOCKED",
            activation_ready=False,
            blocker="FUTURE_PUBLICATION_FORBIDDEN",
        ),
    )

    assert (
        bridge.build_bank_daily_production_context(
            _record()
        )
        is None
    )


def test_non_null_blocker_fails_closed(
    monkeypatch,
):
    monkeypatch.setattr(
        bridge,
        "evaluate_bank_production_source",
        lambda record: _onboarding_result(
            blocker="UNEXPECTED_BLOCKER",
        ),
    )

    assert (
        bridge.build_bank_daily_production_context(
            _record()
        )
        is None
    )


def test_bridge_does_not_mutate_input(
    monkeypatch,
):
    record = _record()
    original = deepcopy(record)

    monkeypatch.setattr(
        bridge,
        "evaluate_bank_production_source",
        lambda record: _onboarding_result(),
    )

    bridge.build_bank_daily_production_context(
        record
    )

    assert record == original


def test_context_is_frozen(
    monkeypatch,
):
    monkeypatch.setattr(
        bridge,
        "evaluate_bank_production_source",
        lambda record: _onboarding_result(),
    )

    result = bridge.build_bank_daily_production_context(
        _record()
    )

    assert result is not None

    with pytest.raises(AttributeError):
        result.symbol = "AKBNK"