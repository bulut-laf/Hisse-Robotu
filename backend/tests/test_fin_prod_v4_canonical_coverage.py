import json
from pathlib import Path

from app.analysis.financial_intelligence_canonical_coverage_v4 import (
    SHORT_TERM_BLOCKER,
    LONG_TERM_BLOCKER,
    inspect_symbol_coverage,
    enrich_v3_batch,
)


def _root(repo: Path) -> Path:
    p = repo / "backend" / "data" / "financial_intelligence"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_short(repo: Path, symbol="TUPRS", **overrides):
    payload = {
        "symbol": symbol,
        "as_of_date": "2026-09-04",
        "canonical": True,
        "technical_context": {"status": "PASS"},
        "market_context": {"status": "PASS"},
        "data_quality": {"status": "PASS"},
    }
    payload.update(overrides)
    (_root(repo) / f"{symbol}_short_term_canonical_context.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _write_long(repo: Path, symbol="TUPRS", **overrides):
    payload = {
        "symbol": symbol,
        "as_of_date": "2026-09-04",
        "canonical": True,
        "business_quality": {"status": "PASS"},
        "governance": {"status": "PASS"},
        "growth_context": {"status": "PASS"},
        "data_quality": {"status": "PASS"},
    }
    payload.update(overrides)
    (_root(repo) / f"{symbol}_long_term_canonical_coverage.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _v3(symbol="TUPRS", status="READY_FOR_DECISION_SUPPORT"):
    return {
        "status": "PASS",
        "schema_version": "fin-prod-v3-live-batch-v1",
        "symbols": [{
            "symbol": symbol,
            "sector_profile": "INDUSTRIAL",
            "decision_support_status": status,
        }],
    }


def test_missing_artifacts_preserve_both_blockers(tmp_path):
    cov = inspect_symbol_coverage(repo=tmp_path, symbol="TUPRS")
    assert cov.unresolved_blockers == (SHORT_TERM_BLOCKER, LONG_TERM_BLOCKER)
    assert cov.coverage_status == "BLOCKED_CANONICAL_COVERAGE"


def test_short_term_partial_evidence_does_not_pass(tmp_path):
    _write_short(tmp_path, market_context={"status": "MISSING"})
    cov = inspect_symbol_coverage(repo=tmp_path, symbol="TUPRS")
    assert cov.short_term.status == "BLOCKED"
    assert "market_context" in cov.short_term.missing_fields
    assert SHORT_TERM_BLOCKER in cov.unresolved_blockers


def test_complete_canonical_coverage_unlocks_full_readiness(tmp_path):
    _write_short(tmp_path)
    _write_long(tmp_path)
    out = enrich_v3_batch(repo=tmp_path, v3_batch=_v3())
    assert out["ready_full_symbols"] == ["TUPRS"]
    assert out["symbols"][0]["decision_support_status_v4"] == "READY_FULL_DECISION_SUPPORT"
    assert out["symbols"][0]["canonical_coverage_v4"]["unresolved_blockers"] == ()


def test_upstream_source_block_cannot_be_overridden(tmp_path):
    _write_short(tmp_path)
    _write_long(tmp_path)
    out = enrich_v3_batch(repo=tmp_path, v3_batch=_v3(status="BLOCKED_SOURCE"))
    assert out["ready_full_symbols"] == []
    assert out["symbols"][0]["decision_support_status_v4"] == "BLOCKED_SOURCE"


def test_wrong_symbol_and_noncanonical_are_fail_closed(tmp_path):
    _write_short(tmp_path, symbol="AAA")
    # Rename artifact so TUPRS loader sees payload mismatch.
    src = _root(tmp_path) / "AAA_short_term_canonical_context.json"
    dst = _root(tmp_path) / "TUPRS_short_term_canonical_context.json"
    src.rename(dst)
    _write_long(tmp_path, canonical=False)
    cov = inspect_symbol_coverage(repo=tmp_path, symbol="TUPRS")
    assert "symbol" in cov.short_term.missing_fields
    assert "canonical" in cov.long_term.missing_fields
    assert cov.coverage_status == "BLOCKED_CANONICAL_COVERAGE"
