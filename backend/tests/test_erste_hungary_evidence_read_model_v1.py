import json
from pathlib import Path

from backend.app.funds.erste_hungary_evidence_read_model import (
    ErsteHungaryEvidenceReadModel,
)


ROOT = Path(r"D:\Projects\Hisse-Robotu")
ARTIFACT = (
    ROOT
    / "_discovery"
    / "erste_hungary"
    / "f1_f2_f3_f4_evidence_v1_latest.json"
)


def test_fh15_artifact_has_929_rows():
    rows = ErsteHungaryEvidenceReadModel(ARTIFACT).rows()
    assert len(rows) == 929


def test_fh15_trade_authority_and_forced_fill_invariants():
    rows = ErsteHungaryEvidenceReadModel(ARTIFACT).rows()
    assert all(row.automatic_trade_authority == "NONE" for row in rows)
    assert all(row.forced_fill is False for row in rows)


def test_fh15_f5_is_safe_unavailable_and_not_synthesized():
    rows = ErsteHungaryEvidenceReadModel(ARTIFACT).rows()
    assert all(row.f5_state == "SAFE_UNAVAILABLE" for row in rows)


def test_fh15_classification_counts_are_frozen():
    rows = ErsteHungaryEvidenceReadModel(ARTIFACT).rows()
    counts = {}
    for row in rows:
        counts[row.classification] = counts.get(row.classification, 0) + 1
    assert counts == {"A": 6, "B": 175, "C": 399, "D": 321, "X": 28}


def test_fh15_f4_counts_are_frozen():
    rows = ErsteHungaryEvidenceReadModel(ARTIFACT).rows()
    counts = {}
    for row in rows:
        counts[row.f4_state] = counts.get(row.f4_state, 0) + 1
    assert counts == {
        "CAUTION": 51,
        "NEUTRAL": 122,
        "POSITIVE": 105,
        "UNAVAILABLE": 651,
    }


def test_fh15_by_fund_is_read_only_lookup():
    model = ErsteHungaryEvidenceReadModel(ARTIFACT)
    first = model.rows()[0]
    found = model.by_fund(first.canonical_fund_id)
    assert found == first