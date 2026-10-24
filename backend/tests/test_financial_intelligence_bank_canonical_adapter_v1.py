from app.analysis.financial_intelligence_bank_model_contract import (
    BANK_COMPONENTS,
    BANK_REQUIRED_METRICS,
)
from app.analysis.financial_intelligence_bank_canonical_adapter import (
    adapt_bank_canonical_input,
)


def _record():
    facts = {}

    for component in BANK_COMPONENTS:
        for metric in BANK_REQUIRED_METRICS[
            component
        ]:
            facts[
                f"{component}.{metric}"
            ] = 1.0

    return {
        "symbol": "TESTB",
        "sector_model": "BANK",
        "as_of": "2026-08-31",
        "publication_date": "2026-08-15",
        "canonical_facts": facts,
    }


def test_complete_canonical_bank_record_passes():

    result = adapt_bank_canonical_input(
        _record()
    )

    assert result.status == "PASS"
    assert result.symbol == "TESTB"
    assert result.payload is not None
    assert result.blocker is None


def test_future_publication_fails_closed():

    record = _record()
    record["publication_date"] = "2026-09-01"

    result = adapt_bank_canonical_input(
        record
    )

    assert result.status == "BLOCKED"
    assert result.payload is None
    assert (
        result.blocker
        == "FUTURE_PUBLICATION_FORBIDDEN"
    )


def test_sector_mismatch_fails_closed():

    record = _record()
    record["sector_model"] = "INDUSTRIAL"

    result = adapt_bank_canonical_input(
        record
    )

    assert result.status == "BLOCKED"
    assert (
        result.blocker
        == "SECTOR_MODEL_MISMATCH:INDUSTRIAL"
    )


def test_missing_canonical_metric_fails_closed():

    record = _record()

    record["canonical_facts"].pop(
        "ASSET_QUALITY.npl_ratio"
    )

    result = adapt_bank_canonical_input(
        record
    )

    assert result.status == "BLOCKED"
    assert result.payload is None

    assert (
        result.blocker
        == "BANK_CANONICAL_METRIC_MISSING:"
           "ASSET_QUALITY.npl_ratio"
    )


def test_missing_never_becomes_zero():

    record = _record()

    record["canonical_facts"][
        "PROFITABILITY.roe"
    ] = None

    result = adapt_bank_canonical_input(
        record
    )

    assert result.status == "BLOCKED"
    assert result.payload is None
    assert "PROFITABILITY.roe" in result.blocker
