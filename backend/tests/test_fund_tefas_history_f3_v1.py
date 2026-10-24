from decimal import Decimal

import pytest

from backend.app.funds.evidence_mapper import (
    EvidenceState,
    FundEvidenceInput,
    map_fund_evidence,
)
import backend.app.funds.tefas_history_f3 as f3


def source(
    code: str,
) -> FundEvidenceInput:
    return FundEvidenceInput(
        canonical_fund_id=f"TEFAS:{code}",
        category_id=None,

        category_rank_percentile=None,
        category_rank_change=None,

        return_1m=Decimal("0.01"),
        return_3m=Decimal("0.03"),
        return_6m=Decimal("0.05"),

        volatility_percentile=None,
        max_drawdown=None,

        fund_size_change=None,
        investor_change=None,
        net_flow_ratio=None,

        total_expense_ratio=None,
        regime_fit=None,
        allocation_known=False,
    )


def row(
    code: str,
    day: str,
    price: object,
) -> dict[str, object]:
    return {
        "fonKodu": code,
        "fonUnvan": "TEST",
        "kategoriDerece": 0,
        "kategoriFonSay": 29,
        "tarih": day,
        "fiyat": price,
    }


def test_verified_tefas_history_schema_maps_price_series():
    rows = (
        row("AU1", "2026-08-05", 1.127584),
        row("AU1", "2026-08-03", 1.099958),
        row("AU1", "2026-08-04", 1.111404),
    )

    points = f3.parse_tefas_history_rows(
        rows,
        expected_fund_code="AU1",
    )

    assert tuple(
        item.observation_date.isoformat()
        for item in points
    ) == (
        "2026-08-03",
        "2026-08-04",
        "2026-08-05",
    )

    assert tuple(
        item.unit_price
        for item in points
    ) == (
        Decimal("1.099958"),
        Decimal("1.111404"),
        Decimal("1.127584"),
    )


def test_category_fields_are_not_used_for_f3():
    rows = (
        row("AU1", "2026-08-03", "100"),
        row("AU1", "2026-08-04", "101"),
        row("AU1", "2026-08-05", "102"),
    )

    rows[0]["kategoriDerece"] = 999999
    rows[0]["kategoriFonSay"] = 999999

    prices = f3.price_series_from_tefas_history_rows(
        rows,
        expected_fund_code="AU1",
    )

    assert prices == (
        Decimal("100"),
        Decimal("101"),
        Decimal("102"),
    )


def test_duplicate_history_date_fails_closed():
    rows = (
        row("AU1", "2026-08-03", "100"),
        row("AU1", "2026-08-03", "101"),
    )

    with pytest.raises(
        ValueError,
        match="F3_HISTORY_DUPLICATE_DATE",
    ):
        f3.parse_tefas_history_rows(
            rows,
            expected_fund_code="AU1",
        )


def test_missing_verified_field_fails_closed():
    broken = row(
        "AU1",
        "2026-08-03",
        "100",
    )

    del broken["fiyat"]

    with pytest.raises(
        ValueError,
        match="F3_HISTORY_SCHEMA_MISSING:fiyat",
    ):
        f3.parse_tefas_history_rows(
            (broken,),
            expected_fund_code="AU1",
        )


def test_exact_provider_contract_is_reused(
    monkeypatch,
):
    calls = []

    def fake_fetch(
        fund_code,
        *,
        period=1,
        timeout_seconds=10,
    ):
        calls.append(
            (
                fund_code,
                period,
                timeout_seconds,
            )
        )

        return (
            row("AU1", "2026-08-03", "100"),
            row("AU1", "2026-08-04", "101"),
            row("AU1", "2026-08-05", "102"),
        )

    monkeypatch.setattr(
        f3,
        "fetch_tefas_fund_history_rows",
        fake_fetch,
    )

    prices = f3.fetch_tefas_price_series(
        "au1",
        period=1,
        timeout_seconds=7,
    )

    assert calls == [
        ("AU1", 1, 7)
    ]

    assert len(prices) == 3


def test_history_to_f3_evidence_end_to_end():
    inputs = {
        "AAA": source("AAA"),
        "BBB": source("BBB"),
    }

    histories = {
        "AAA": (
            row("AAA", "2026-08-01", "100"),
            row("AAA", "2026-08-02", "101"),
            row("AAA", "2026-08-03", "102"),
            row("AAA", "2026-08-04", "103"),
            row("AAA", "2026-08-05", "104"),
        ),
        "BBB": (
            row("BBB", "2026-08-01", "100"),
            row("BBB", "2026-08-02", "120"),
            row("BBB", "2026-08-03", "80"),
            row("BBB", "2026-08-04", "130"),
            row("BBB", "2026-08-05", "70"),
        ),
    }

    enriched = f3.enrich_f3_inputs_from_tefas_histories(
        inputs,
        histories,
    )

    by_id = {
        item.canonical_fund_id: item
        for item in enriched
    }

    low = map_fund_evidence(
        by_id["TEFAS:AAA"]
    ).evidence[2]

    high = map_fund_evidence(
        by_id["TEFAS:BBB"]
    ).evidence[2]

    assert low.family == "F3"
    assert low.state is EvidenceState.POSITIVE

    assert high.family == "F3"
    assert high.state is EvidenceState.CAUTION


def test_missing_history_keeps_f3_unavailable():
    enriched = (
        f3.enrich_f3_inputs_from_tefas_histories(
            {
                "AAA": source("AAA"),
            },
            {},
        )[0]
    )

    evidence = map_fund_evidence(
        enriched
    ).evidence[2]

    assert evidence.state is EvidenceState.UNAVAILABLE
    assert enriched.volatility_percentile is None
    assert enriched.max_drawdown is None
