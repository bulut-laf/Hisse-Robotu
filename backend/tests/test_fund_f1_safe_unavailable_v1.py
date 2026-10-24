from decimal import Decimal

from backend.app.funds.evidence_mapper import (
    EvidenceState,
    FundEvidenceInput,
    map_fund_evidence,
)
from backend.app.funds.live_pipeline import (
    evidence_from_tefas_rows,
)


def test_f1_requires_verified_rank_and_rank_change():
    value = FundEvidenceInput(
        canonical_fund_id="fund:tefas:AAA",
        category_id="example-category",
        category_rank_percentile=None,
        category_rank_change=None,
        return_1m=None,
        return_3m=None,
        return_6m=None,
        volatility_percentile=None,
        max_drawdown=None,
        fund_size_change=None,
        investor_change=None,
        net_flow_ratio=None,
        total_expense_ratio=None,
        regime_fit=None,
        allocation_known=False,
    )

    f1 = map_fund_evidence(value).evidence[0]

    assert f1.family == "F1"
    assert f1.state is EvidenceState.UNAVAILABLE
    assert "category_rank_percentile" in f1.missing_fields
    assert "category_rank_change" in f1.missing_fields


def test_tefas_category_fields_are_not_guessed_into_f1():
    rows = (
        {
            "fonkod": "AAA",
            "fonunvan": "TEST FONU",
            "fonKategori": "TEST KATEGORI",
            "kategoriDerece": 1,
            "kategoriFonSay": 20,
            "getiri1a": 1.0,
            "getiri3a": 2.0,
            "getiri6a": 3.0,
        },
    )

    mapped = evidence_from_tefas_rows(rows)

    assert len(mapped) == 1

    f1 = mapped[0].evidence[0]

    # kategoriDerece / kategoriFonSay semantics and temporal
    # rank-change contract are not proven; no inference allowed.
    assert f1.state is EvidenceState.UNAVAILABLE


def test_f1_does_not_block_f2():
    rows = (
        {
            "fonkod": "AAA",
            "fonunvan": "TEST FONU",
            "fonKategori": "TEST KATEGORI",
            "kategoriDerece": 1,
            "kategoriFonSay": 20,
            "getiri1a": 1.0,
            "getiri3a": 2.0,
            "getiri6a": 3.0,
        },
    )

    mapped = evidence_from_tefas_rows(rows)[0]

    f1 = mapped.evidence[0]
    f2 = mapped.evidence[1]

    assert f1.state is EvidenceState.UNAVAILABLE
    assert f2.state is EvidenceState.POSITIVE
