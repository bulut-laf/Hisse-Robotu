from decimal import Decimal
from pathlib import Path

from backend.app.funds.evidence_mapper import (
    EvidenceState,
    FundEvidenceInput,
    map_fund_evidence,
)
from backend.app.funds.live_pipeline import (
    evidence_from_tefas_rows,
)


def source(**changes):
    payload = dict(
        canonical_fund_id="fund:tefas:AAA",
        category_id=None,
        category_rank_percentile=None,
        category_rank_change=None,
        return_1m=Decimal("0.01"),
        return_3m=Decimal("0.02"),
        return_6m=Decimal("0.03"),
        volatility_percentile=None,
        max_drawdown=None,
        fund_size_change=None,
        investor_change=None,
        net_flow_ratio=None,
        total_expense_ratio=None,
        regime_fit=None,
        allocation_known=False,
    )

    payload.update(changes)

    return FundEvidenceInput(
        **payload
    )


def f5(value):
    mapped = map_fund_evidence(
        value
    )

    return next(
        item
        for item in mapped.evidence
        if item.family == "F5"
    )


def test_missing_all_f5_sources_is_unavailable():
    item = f5(
        source()
    )

    assert item.state is EvidenceState.UNAVAILABLE

    assert item.missing_fields == (
        "allocation",
        "regime_fit",
        "total_expense_ratio",
    )


def test_cost_alone_cannot_activate_f5():
    item = f5(
        source(
            total_expense_ratio=Decimal(
                "0.01"
            ),
        )
    )

    assert item.state is EvidenceState.UNAVAILABLE
    assert "regime_fit" in item.missing_fields
    assert "allocation" in item.missing_fields


def test_regime_alone_cannot_activate_f5():
    item = f5(
        source(
            regime_fit=Decimal(
                "0.8"
            ),
        )
    )

    assert item.state is EvidenceState.UNAVAILABLE
    assert "total_expense_ratio" in item.missing_fields
    assert "allocation" in item.missing_fields


def test_allocation_alone_cannot_activate_f5():
    item = f5(
        source(
            allocation_known=True,
        )
    )

    assert item.state is EvidenceState.UNAVAILABLE

    assert item.missing_fields == (
        "regime_fit",
        "total_expense_ratio",
    )


def test_two_of_three_still_cannot_activate_f5():
    item = f5(
        source(
            total_expense_ratio=Decimal(
                "0.01"
            ),
            regime_fit=Decimal(
                "0.8"
            ),
            allocation_known=False,
        )
    )

    assert item.state is EvidenceState.UNAVAILABLE
    assert item.missing_fields == (
        "allocation",
    )


def test_live_universe_mapping_does_not_invent_f5():
    rows = (
        {
            "fonkod": "AAA",
            "fonunvan": "TEST",
            "getiri1a": 1,
            "getiri3a": 2,
            "getiri6a": 3,
        },
    )

    mapped = evidence_from_tefas_rows(
        rows
    )

    assert len(mapped) == 1

    item = next(
        evidence
        for evidence
        in mapped[0].evidence
        if evidence.family == "F5"
    )

    assert item.state is EvidenceState.UNAVAILABLE

    assert item.missing_fields == (
        "allocation",
        "regime_fit",
        "total_expense_ratio",
    )


def test_no_f5_source_adapter_has_been_silently_added():
    root = Path(
        "backend/app/funds"
    )

    provider_files = (
        "tefas_adapter.py",
        "f4_snapshot.py",
    )

    provider_text = "\n".join(
        (
            root / name
        ).read_text(
            encoding="utf-8-sig"
        )
        for name in provider_files
        if (
            root / name
        ).exists()
    )

    assert "total_expense_ratio=" not in provider_text
    assert "regime_fit=" not in provider_text
    assert "allocation_known=True" not in provider_text
