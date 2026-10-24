import json
from pathlib import Path

from app.analysis.financial_intelligence_live_pipeline_v3 import (
    discover_symbols,
    build_live_batch,
)


def _write_acceptance(repo: Path, symbol: str, period: str = "2026_2"):
    data = repo / "backend" / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / f"financial_intelligence_acceptance_{symbol}_{period}.json").write_text(
        json.dumps({"status": "PASS"}),
        encoding="utf-8",
    )


def test_discover_symbols_only_from_canonical_acceptance(tmp_path):
    _write_acceptance(tmp_path, "AAA")
    _write_acceptance(tmp_path, "BBB")
    (tmp_path / "backend" / "data" / "random_CCC.json").write_text("{}", encoding="utf-8")
    assert discover_symbols(tmp_path) == ("AAA", "BBB")


def test_live_batch_fail_closed_for_missing_downstream(tmp_path):
    _write_acceptance(tmp_path, "AAA")
    payload = build_live_batch(
        repo=tmp_path,
        sector_map={"AAA": "INDUSTRIAL"},
    )
    assert payload["status"] == "PASS"
    assert payload["summary"]["total_symbols"] == 1
    assert payload["symbols"][0]["symbol"] == "AAA"
    assert payload["symbols"][0]["decision_support_status"] == "READY_FINANCIAL_CORE_ONLY"


def test_explicit_symbol_source(tmp_path):
    payload = build_live_batch(
        repo=tmp_path,
        symbols=("ZZZ",),
        sector_map={"ZZZ": "BANK"},
    )
    assert payload["symbol_source"] == "EXPLICIT"
    assert payload["symbols"][0]["sector_profile"] == "BANK"
    assert payload["symbols"][0]["decision_support_status"] == "BLOCKED_SOURCE"


def test_tuprs_ready_when_v2_artifacts_exist(tmp_path):
    _write_acceptance(tmp_path, "TUPRS")

    fi = tmp_path / "backend" / "data" / "financial_intelligence"
    fi.mkdir(parents=True, exist_ok=True)

    (fi / "TUPRS_investability_production_closure.json").write_text(
        json.dumps({
            "status": "PASS_CLOSED_WITH_EXPLICIT_BLOCKERS",
            "unresolved_blockers": [
                "SHORT_TERM_CANONICAL_TECHNICAL_MARKET_CONTEXT",
                "LONG_TERM_CANONICAL_COVERAGE",
            ],
        }),
        encoding="utf-8",
    )

    payload = build_live_batch(
        repo=tmp_path,
        sector_map={"TUPRS": "INDUSTRIAL"},
    )
    assert payload["ready_symbols"] == ["TUPRS"]
    assert payload["summary"]["ready_for_decision_support"] == 1
