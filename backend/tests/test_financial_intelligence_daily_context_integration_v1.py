from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.analysis.financial_intelligence_daily_context import (
    build_financial_intelligence_daily_context,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
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
def test_real_bank_bundle_attaches_to_daily_fi_context(
    filename,
    symbol,
):
    path = DATA_DIR / filename

    assert path.exists(), f"Missing bundle: {path}"

    record = _record_from_bundle(path)

    context = build_financial_intelligence_daily_context(
        PROJECT_ROOT,
        symbol,
        bank_record=record,
    )

    assert context.symbol == symbol
    assert context.bank is not None
    assert context.bank.symbol == symbol
    assert context.bank.canonical_input_ready is True
    assert context.bank.scoring_ready is True
    assert context.bank.production_evidence is True
    assert context.bank.activation_ready is True

    assert context.panel is not None
    assert isinstance(context.panel, dict)


def test_akbnk_and_garan_are_independent_daily_contexts():
    contexts = []

    for filename, symbol in (
        (
            "AKBNK_2026Q2_OFFICIAL_EVIDENCE_BUNDLE.json",
            "AKBNK",
        ),
        (
            "GARAN_2026Q2_OFFICIAL_EVIDENCE_BUNDLE.json",
            "GARAN",
        ),
    ):
        path = DATA_DIR / filename
        record = _record_from_bundle(path)

        context = build_financial_intelligence_daily_context(
            PROJECT_ROOT,
            symbol,
            bank_record=record,
        )

        assert context.bank is not None
        contexts.append(context)

    assert {item.symbol for item in contexts} == {
        "AKBNK",
        "GARAN",
    }

    assert all(
        item.bank is not None
        and item.bank.activation_ready is True
        for item in contexts
    )


def test_bank_record_cannot_attach_to_wrong_symbol():
    path = (
        DATA_DIR
        / "GARAN_2026Q2_OFFICIAL_EVIDENCE_BUNDLE.json"
    )

    record = _record_from_bundle(path)

    context = build_financial_intelligence_daily_context(
        PROJECT_ROOT,
        "AKBNK",
        bank_record=record,
    )

    assert context.symbol == "AKBNK"
    assert context.bank is None
    assert context.panel is not None