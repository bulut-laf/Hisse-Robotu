
from datetime import date
import json
from decimal import Decimal

from backend.app.analysis import fin_prod_v5_short_term_context_adapter as m


def test_rev7_exact_momentum_mapping_ignores_teknik_skor(tmp_path):
    fi = tmp_path / "financial_intelligence"
    fi.mkdir()

    p = fi / "TUPRS_momentum_candidate_2026-08-04.json"
    p.write_text(
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

    values, evidence, source = m._exact_momentum_artifact(
        data_root=tmp_path,
        symbol="TUPRS",
        as_of_date=date(2026, 8, 4),
    )

    assert values["technical_trend"] == Decimal("15")
    assert values["relative_strength"] == Decimal("20")
    assert values["volume_liquidity"] == Decimal("10")
    assert evidence["technical_trend"]["key"] == "trend_puani"
    assert "teknik_skor" not in evidence["technical_trend"]["key"]


def test_rev7_wrong_as_of_fails_closed(tmp_path):
    fi = tmp_path / "financial_intelligence"
    fi.mkdir()

    p = fi / "TUPRS_momentum_candidate_2026-08-04.json"
    p.write_text(
        json.dumps({
            "status": "PASS",
            "symbol": "TUPRS",
            "as_of_date": "2026-08-05",
            "candidate": {
                "trend_puani": 15,
                "goreceli_guc_puani": 20,
                "likidite_puani": 10,
            },
        }),
        encoding="utf-8",
    )

    values, evidence, _ = m._exact_momentum_artifact(
        data_root=tmp_path,
        symbol="TUPRS",
        as_of_date=date(2026, 8, 4),
    )

    assert values["technical_trend"] is None
    assert evidence["technical_trend"]["status"] == "POINT_IN_TIME_OR_CANDIDATE_INVALID"
