from pathlib import Path

from app.analysis.financial_intelligence_symbol_selector import (
    build_financial_intelligence_symbol_selector,
)


def test_selector_reads_registry_and_returns_tuprs():
    root = Path(__file__).resolve().parents[2]
    data = build_financial_intelligence_symbol_selector(root)

    assert data["status"] == "PASS"
    assert data["mode"] == "READ_ONLY_SELECTOR"
    assert "TUPRS" in data["symbols"]
    assert data["default_symbol"] == "TUPRS"
    assert data["symbol_count"] >= 1


def test_selector_is_deterministic_and_sorted():
    root = Path(__file__).resolve().parents[2]
    data = build_financial_intelligence_symbol_selector(root)

    assert data["symbols"] == sorted(data["symbols"])
    assert len(data["symbols"]) == len(set(data["symbols"]))
