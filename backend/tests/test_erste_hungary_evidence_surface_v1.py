from pathlib import Path

from backend.app.funds.erste_hungary_evidence_surface import (
    erste_hungary_evidence_as_of,
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



def test_surface_normalizes_enum_repr_states_at_boundary(tmp_path):
    import json

    artifact = tmp_path / "enum_repr.json"
    source = {
        "as_of": "2026-09-25",
        "automatic_trade_authority": "NONE",
        "canonical_fund_id": "fund:isin:TESTENUM0001",
        "category_id": "EQUITY",
        "classification": "C",
        "eligibility_reason": "TEST",
        "f1_state": "EvidenceState.CAUTION",
        "f2_state": "EvidenceState.POSITIVE",
        "f3_state": "EvidenceState.NEUTRAL",
        "f4_latest_date": "2026-09-25",
        "f4_previous_date": "2026-09-18",
        "f4_state": "EvidenceState.UNAVAILABLE",
        "forced_fill": False,
        "instrument_id": "TESTENUM0001",
        "isin": "TESTENUM0001",
    }
    artifact.write_text(json.dumps([source]), encoding="utf-8")

    rows = load_erste_hungary_evidence_surface(artifact)

    assert len(rows) == 1
    assert rows[0].f1_state == "CAUTION"
    assert rows[0].f2_state == "POSITIVE"
    assert rows[0].f3_state == "NEUTRAL"
    assert rows[0].f4_state == "UNAVAILABLE"

def test_surface_exposes_artifact_as_of_provenance():
    rows = load_erste_hungary_evidence_surface(ARTIFACT)
    assert erste_hungary_evidence_as_of(rows) == "MIXED"


def test_surface_marks_mixed_artifact_dates_without_deriving_a_date(tmp_path):
    import json

    artifact = tmp_path / "mixed_dates.json"
    base = {
        "as_of": "2026-09-25",
        "automatic_trade_authority": "NONE",
        "canonical_fund_id": "fund:isin:TESTPROV0001",
        "category_id": "EQUITY",
        "classification": "C",
        "eligibility_reason": "TEST",
        "f1_state": "CAUTION",
        "f2_state": "POSITIVE",
        "f3_state": "NEUTRAL",
        "f4_latest_date": "2026-09-25",
        "f4_previous_date": "2026-09-18",
        "f4_state": "UNAVAILABLE",
        "forced_fill": False,
        "instrument_id": "TESTPROV0001",
        "isin": "TESTPROV0001",
    }
    second = dict(base)
    second["canonical_fund_id"] = "fund:isin:TESTPROV0002"
    second["instrument_id"] = "TESTPROV0002"
    second["isin"] = "TESTPROV0002"
    second["as_of"] = "2026-09-24"

    artifact.write_text(json.dumps([base, second]), encoding="utf-8")
    rows = load_erste_hungary_evidence_surface(artifact)

    assert erste_hungary_evidence_as_of(rows) == "MIXED"
