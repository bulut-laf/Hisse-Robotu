from pathlib import Path

from backend.app.funds.erste_hungary_evidence_surface import (
    erste_hungary_evidence_rows,
    load_erste_hungary_evidence_surface,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = (
    ROOT
    / "_discovery"
    / "erste_hungary"
    / "f1_f2_f3_f4_evidence_v1_latest.json"
)


def test_surface_loads_current_artifact():
    rows = load_erste_hungary_evidence_surface(ARTIFACT)
    assert len(rows) == 929


def test_surface_preserves_classification_counts():
    rows = load_erste_hungary_evidence_surface(ARTIFACT)
    counts = {key: sum(row.classification == key for row in rows) for key in "ABCDX"}
    assert counts == {"A": 6, "B": 175, "C": 399, "D": 321, "X": 28}


def test_surface_preserves_safety_invariants():
    rows = load_erste_hungary_evidence_surface(ARTIFACT)
    assert all(row.automatic_trade_authority == "NONE" for row in rows)
    assert all(not row.forced_fill for row in rows)
    assert all(row.f5_state == "SAFE_UNAVAILABLE" for row in rows)


def test_display_rows_keep_evidence_and_no_trade_authority():
    rows = load_erste_hungary_evidence_surface(ARTIFACT)
    display = erste_hungary_evidence_rows(rows[:1])[0]
    assert display["Yetki"] == "NONE"
    assert display["Forced Fill"] == "NO"
    assert display["F5"] == "SAFE_UNAVAILABLE"
    assert "AL" not in display and "SAT" not in display


def test_surface_preserves_all_f1_f4_fields():
    rows = load_erste_hungary_evidence_surface(ARTIFACT)
    assert all(row.f1_state in {"POSITIVE", "NEUTRAL", "CAUTION"} for row in rows)
    assert all(row.f2_state in {"POSITIVE", "NEUTRAL", "CAUTION", "UNAVAILABLE"} for row in rows)
    assert all(row.f3_state in {"POSITIVE", "NEUTRAL", "CAUTION", "UNAVAILABLE"} for row in rows)
    assert all(row.f4_state in {"POSITIVE", "NEUTRAL", "CAUTION", "UNAVAILABLE"} for row in rows)

