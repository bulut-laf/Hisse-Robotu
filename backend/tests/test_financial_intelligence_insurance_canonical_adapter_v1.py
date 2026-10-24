from app.analysis.financial_intelligence_insurance_model_contract import (
    INSURANCE_COMPONENTS,
    INSURANCE_REQUIRED_METRICS,
)
from app.analysis.financial_intelligence_insurance_canonical_adapter import (
    adapt_insurance_canonical_input,
)


def _record():
    facts = {}

    for component in INSURANCE_COMPONENTS:
        for metric in INSURANCE_REQUIRED_METRICS[component]:
            facts[f"{component}.{metric}"] = 1.0

    return {
        "symbol": "TESTI",
        "sector_model": "INSURANCE",
        "as_of": "2026-08-31",
        "publication_date": "2026-08-15",
        "canonical_facts": facts,
    }


def test_complete_insurance_canonical_record_passes():
    result = adapt_insurance_canonical_input(_record())

    assert result.status == "PASS"
    assert result.symbol == "TESTI"
    assert result.payload is not None
    assert result.blocker is None


def test_future_publication_fails_closed():
    record = _record()
    record["publication_date"] = "2026-09-01"

    result = adapt_insurance_canonical_input(record)

    assert result.status == "BLOCKED"
    assert result.payload is None
    assert result.blocker == "FUTURE_PUBLICATION_FORBIDDEN"


def test_sector_mismatch_fails_closed():
    record = _record()
    record["sector_model"] = "INDUSTRIAL"

    result = adapt_insurance_canonical_input(record)

    assert result.status == "BLOCKED"
    assert result.blocker == "SECTOR_MODEL_MISMATCH:INDUSTRIAL"


def test_missing_canonical_metric_fails_closed():
    record = _record()
    record["canonical_facts"].pop(
        "UNDERWRITING_QUALITY.combined_ratio"
    )

    result = adapt_insurance_canonical_input(record)

    assert result.status == "BLOCKED"
    assert result.payload is None
    assert result.blocker == (
        "INSURANCE_CANONICAL_METRIC_MISSING:"
        "UNDERWRITING_QUALITY.combined_ratio"
    )


def test_missing_never_becomes_zero():
    record = _record()
    record["canonical_facts"][
        "PROFITABILITY.roe"
    ] = None

    result = adapt_insurance_canonical_input(record)

    assert result.status == "BLOCKED"
    assert result.payload is None
    assert "PROFITABILITY.roe" in result.blocker
