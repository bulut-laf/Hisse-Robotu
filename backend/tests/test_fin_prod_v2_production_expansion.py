import json
from pathlib import Path

from app.analysis.financial_intelligence_production_v2 import (
    resolve_sector_profile,
    build_symbol_manifest,
    build_batch_manifest,
)


def test_sector_routing():
    assert resolve_sector_profile("BANKA")[0] == "BANK"
    assert resolve_sector_profile("GYO")[0] == "REIT"
    assert resolve_sector_profile("ENERJI")[0] == "UTILITY_ENERGY"
    assert resolve_sector_profile("UNKNOWN")[0] == "GENERIC"


def test_missing_source_is_fail_closed(tmp_path):
    repo = tmp_path
    m = build_symbol_manifest(repo=repo, symbol="ABC", sector="INDUSTRIAL")
    assert m.decision_support_status == "BLOCKED_SOURCE"
    assert "FINANCIAL_CORE_MISSING" in m.blockers


def test_tuprs_like_manifest(tmp_path):
    repo = tmp_path
    data = repo / "backend" / "data"
    fi = data / "financial_intelligence"
    fi.mkdir(parents=True)

    (data / "financial_intelligence_acceptance_TUPRS_2026_2.json").write_text(
        json.dumps({"status": "PASS"}), encoding="utf-8"
    )
    (fi / "TUPRS_fair_value_acceptance.json").write_text(
        json.dumps({"status": "PASS"}), encoding="utf-8"
    )
    (fi / "TUPRS_investability_production_closure.json").write_text(
        json.dumps({
            "status": "PASS_CLOSED_WITH_EXPLICIT_BLOCKERS",
            "unresolved_blockers": ["SHORT_TERM_CANONICAL_TECHNICAL_MARKET_CONTEXT"],
        }), encoding="utf-8"
    )

    m = build_symbol_manifest(repo=repo, symbol="TUPRS", sector="INDUSTRIAL")
    assert m.decision_support_status == "READY_FOR_DECISION_SUPPORT"
    assert "SHORT_TERM_CANONICAL_TECHNICAL_MARKET_CONTEXT" in m.warnings


def test_batch(tmp_path):
    payload = build_batch_manifest(repo=tmp_path, symbols=["AAA", "BBB"], sector_map={"AAA":"BANK"})
    assert payload["status"] == "PASS"
    assert len(payload["symbols"]) == 2
