from __future__ import annotations

from pathlib import Path

import pytest

from app.analysis.financial_intelligence_bank_daily_production_bridge import (
    build_bank_daily_production_context,
)
from app.analysis.financial_intelligence_bank_official_bundle_record import (
    build_bank_official_bundle_record,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data" / "financial_intelligence"


@pytest.mark.parametrize(
    ("filename", "symbol"),
    (
        (
            "AKBNK_2026Q2_OFFICIAL_EVIDENCE_BUNDLE.json",
            "AKBNK",
        ),
        (
            "GARAN_2026Q2_OFFICIAL_EVIDENCE_BUNDLE.json",
            "GARAN",
        ),
    ),
)
def test_real_bundle_builds_valid_production_record(
    filename,
    symbol,
):
    path = DATA_DIR / filename

    record = build_bank_official_bundle_record(path)

    assert record is not None
    assert record["source_type"] == "OFFICIAL_SOURCE_BUNDLE"
    assert record["symbol"] == symbol
    assert record["source_uri"].startswith("file:")
    assert record["evidence_hash"].startswith("sha256:")
    assert isinstance(record["canonical_facts"], dict)

    context = build_bank_daily_production_context(record)

    assert context is not None
    assert context.symbol == symbol
    assert context.production_evidence is True
    assert context.activation_ready is True


def test_missing_bundle_fails_closed():
    result = build_bank_official_bundle_record(
        DATA_DIR / "MISSING_BUNDLE.json"
    )

    assert result is None