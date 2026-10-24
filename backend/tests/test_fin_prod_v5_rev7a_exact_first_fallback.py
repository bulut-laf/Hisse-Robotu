
from datetime import date
import json

from backend.app.analysis import fin_prod_v5_short_term_context_adapter as m


def test_rev7a_exact_artifact_has_priority_over_generic_aliases(tmp_path, monkeypatch):
    fi = tmp_path / "financial_intelligence"
    fi.mkdir()

    (fi / "TUPRS_momentum_candidate_2026-08-04.json").write_text(
        json.dumps({
            "status": "PASS",
            "symbol": "TUPRS",
            "as_of_date": "2026-08-04",
            "candidate": {
                "trend_puani": 15,
                "teknik_skor": 50,
                "goreceli_guc_puani": 20,
                "likidite_puani": 10,
            },
        }),
        encoding="utf-8",
    )

    (fi / "TUPRS_generic.json").write_text(
        json.dumps({
            "symbol": "TUPRS",
            "as_of_date": "2026-08-04",
            "technical_trend": 99,
            "relative_strength": 99,
            "volume_liquidity": 99,
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

    assert payload["market_context"]["technical_trend"] == "15"
    assert payload["market_context"]["relative_strength"] == "20"
    assert payload["market_context"]["volume_liquidity"] == "10"


def test_rev7a_falls_back_when_exact_artifact_absent(tmp_path, monkeypatch):
    fi = tmp_path / "financial_intelligence"
    fi.mkdir()

    (fi / "TUPRS_generic.json").write_text(
        json.dumps({
            "symbol": "TUPRS",
            "as_of_date": "2026-08-04",
            "technical_trend": 60,
            "relative_strength": 55,
            "volume_liquidity": 50,
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

    assert payload["market_context"]["technical_trend"] == "60"
    assert payload["market_context"]["relative_strength"] == "55"
    assert payload["market_context"]["volume_liquidity"] == "50"
