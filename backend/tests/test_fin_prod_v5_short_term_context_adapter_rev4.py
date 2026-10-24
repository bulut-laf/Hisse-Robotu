
from datetime import date
from pathlib import Path
import json

from backend.app.analysis import fin_prod_v5_short_term_context_adapter as m


def test_own_output_is_never_discovered_as_input(tmp_path):
    fi = tmp_path / "financial_intelligence"
    fi.mkdir()
    own = fi / "TUPRS_short_term_canonical_context.json"
    own.write_text(
        json.dumps({"symbol": "TUPRS", "as_of_date": "2026-09-05"}),
        encoding="utf-8",
    )
    other = fi / "TUPRS_valid_evidence.json"
    other.write_text(
        json.dumps({"symbol": "TUPRS", "as_of_date": "2026-08-04"}),
        encoding="utf-8",
    )

    found = m._discover_symbol_jsons(tmp_path, "TUPRS")
    assert own not in found
    assert other in found


def test_rev4_future_sources_are_excluded_without_false_point_in_time_blocker(tmp_path, monkeypatch):
    fi = tmp_path / "financial_intelligence"
    fi.mkdir()

    valid = fi / "TUPRS_valid.json"
    valid.write_text(
        json.dumps({
            "symbol": "TUPRS",
            "as_of_date": "2026-08-04",
            "technical_trend": "60",
            "relative_strength": "55",
            "volume_liquidity": "50",
        }),
        encoding="utf-8",
    )

    future = fi / "TUPRS_future.json"
    future.write_text(
        json.dumps({
            "symbol": "TUPRS",
            "as_of_date": "2026-09-04",
            "technical_trend": "99",
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        m,
        "discover_exact_canonical_candidates",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        m,
        "_price_reference",
        lambda *a, **k: (
            {
                "market_symbol": "TUPRS.IS",
                "date": "2026-08-04",
                "close": "100",
                "point_in_time_cutoff": "2026-08-04",
            },
            [],
            [],
        ),
    )

    payload = m.build_short_term_canonical_context(
        symbol="TUPRS",
        as_of_date=date(2026, 8, 4),
        data_root=tmp_path,
    )

    assert "POINT_IN_TIME_VIOLATION" not in payload["blockers"]
    assert "FUTURE_CANONICAL_SOURCES_EXCLUDED" in payload["warnings"]
    assert str(future) in payload["excluded_future_sources"]
    assert payload["market_context"]["technical_trend"] == "60"
