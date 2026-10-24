
from datetime import date
from pathlib import Path
import json

from backend.app.analysis import fin_prod_v5_short_term_context_adapter as m


def test_rev5_maps_existing_momentum_candidate_fields_exactly(tmp_path, monkeypatch):
    fi = tmp_path / "financial_intelligence"
    fi.mkdir()

    artifact = fi / "TUPRS_momentum_candidate.json"
    artifact.write_text(
        json.dumps({
            "symbol": "TUPRS",
            "as_of_date": "2026-08-04",
            "trend_puani": 73,
            "goreceli_guc_puani": 68,
            "likidite_puani": 81,
            "hacim_birikimi_puani": 77,
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(m, "discover_exact_canonical_candidates", lambda *a, **k: [])
    monkeypatch.setattr(
        m,
        "_price_reference",
        lambda *a, **k: (
            {
                "market_symbol": "TUPRS.IS",
                "date": "2026-08-04",
                "close": "290.25",
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

    assert payload["market_context"]["technical_trend"] == "73"
    assert payload["market_context"]["relative_strength"] == "68"
    assert payload["market_context"]["volume_liquidity"] == "81"
    assert payload["status"] == "PASS"


def test_rev5_alias_order_does_not_average_distinct_existing_scores():
    docs = [(
        "x.json",
        {
            "likidite_puani": 80,
            "hacim_birikimi_puani": 60,
        },
    )]
    value, evidence = m._extract_exact_metric(
        docs,
        m._EXACT_KEYS["volume_liquidity"],
    )
    assert str(value) == "80"
    assert evidence["key"] == "likidite_puani"


def test_rev5_keeps_missing_as_none():
    docs = [("x.json", {"symbol": "TUPRS"})]
    value, evidence = m._extract_exact_metric(
        docs,
        m._EXACT_KEYS["relative_strength"],
    )
    assert value is None
    assert evidence is None
