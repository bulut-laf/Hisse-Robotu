
import json
from pathlib import Path
from app.analysis.financial_intelligence_canonical_coverage_v4 import inspect_symbol_coverage

def _root(repo: Path) -> Path:
    p = repo / "backend" / "data" / "financial_intelligence"
    p.mkdir(parents=True, exist_ok=True)
    return p

def test_v5_v7a_short_term_schema_is_accepted(tmp_path):
    p = _root(tmp_path)
    (p / "TUPRS_short_term_canonical_context.json").write_text(
        json.dumps({
            "status": "PASS",
            "symbol": "TUPRS",
            "as_of_date": "2026-08-04",
            "market_context": {
                "technical_trend": "15",
                "relative_strength": "20",
                "volume_liquidity": "10",
            },
            "metric_evidence": {
                "technical_trend": {"status": "EXACT_MOMENTUM_CANDIDATE_FIELD", "source": "x.json", "key": "trend_puani"},
                "relative_strength": {"status": "EXACT_MOMENTUM_CANDIDATE_FIELD", "source": "x.json", "key": "goreceli_guc_puani"},
                "volume_liquidity": {"status": "EXACT_MOMENTUM_CANDIDATE_FIELD", "source": "x.json", "key": "likidite_puani"},
            },
            "price_reference": {
                "date": "2026-08-04",
                "point_in_time_cutoff": "2026-08-04",
            },
            "data_quality": "READY",
            "blockers": [],
            "schema_version": "fin-prod-v5-short-term-canonical-context-v7a",
        }),
        encoding="utf-8",
    )
    cov = inspect_symbol_coverage(repo=tmp_path, symbol="TUPRS")
    assert cov.short_term.status == "PASS"
    assert cov.short_term.missing_fields == ()
    assert "SHORT_TERM_CANONICAL_TECHNICAL_MARKET_CONTEXT" not in cov.unresolved_blockers

def test_v5_v7a_missing_required_metric_stays_blocked(tmp_path):
    p = _root(tmp_path)
    (p / "TUPRS_short_term_canonical_context.json").write_text(
        json.dumps({
            "status": "PASS",
            "symbol": "TUPRS",
            "as_of_date": "2026-08-04",
            "market_context": {
                "technical_trend": None,
                "relative_strength": "20",
                "volume_liquidity": "10",
            },
            "metric_evidence": {},
            "price_reference": {
                "date": "2026-08-04",
                "point_in_time_cutoff": "2026-08-04",
            },
            "data_quality": "READY",
            "blockers": [],
            "schema_version": "fin-prod-v5-short-term-canonical-context-v7a",
        }),
        encoding="utf-8",
    )
    cov = inspect_symbol_coverage(repo=tmp_path, symbol="TUPRS")
    assert cov.short_term.status == "BLOCKED"
    assert "SHORT_TERM_CANONICAL_TECHNICAL_MARKET_CONTEXT" in cov.unresolved_blockers
