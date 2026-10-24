from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.analysis.financial_intelligence_bank_daily_production_bridge import (
    build_bank_daily_production_context,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data" / "financial_intelligence"


def _record_from_bundle(path: Path) -> dict:
    raw = path.read_bytes()
    bundle = json.loads(raw.decode("utf-8"))

    return {
        "source_type": "OFFICIAL_SOURCE_BUNDLE",
        "source_uri": path.as_uri(),
        "symbol": bundle["symbol"],
        "sector_model": bundle["sector_model"],
        "period_end": bundle["period_end"],
        "publication_date": bundle["publication_date"],
        "as_of": bundle["as_of"],
        "canonical_facts": bundle["canonical_facts"],
        "evidence_hash": (
            "sha256:" + hashlib.sha256(raw).hexdigest()
        ),
    }


@pytest.mark.parametrize(
    ("filename", "expected_symbol"),
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
def test_real_official_bundle_enters_daily_production_context(
    filename,
    expected_symbol,
):
    path = DATA_DIR / filename

    assert path.exists(), f"Missing official bundle: {path}"

    record = _record_from_bundle(path)

    result = build_bank_daily_production_context(record)

    assert result is not None
    assert result.symbol == expected_symbol
    assert result.source_type == "OFFICIAL_SOURCE_BUNDLE"
    assert result.canonical_input_ready is True
    assert result.scoring_ready is True
    assert result.production_evidence is True
    assert result.activation_ready is True


def test_akbnk_and_garan_real_bundles_are_independently_accepted():
    contexts = []

    for filename in (
        "AKBNK_2026Q2_OFFICIAL_EVIDENCE_BUNDLE.json",
        "GARAN_2026Q2_OFFICIAL_EVIDENCE_BUNDLE.json",
    ):
        path = DATA_DIR / filename
        record = _record_from_bundle(path)

        result = build_bank_daily_production_context(record)

        assert result is not None
        contexts.append(result)

    assert {item.symbol for item in contexts} == {
        "AKBNK",
        "GARAN",
    }

    assert all(
        item.activation_ready is True
        for item in contexts
    )