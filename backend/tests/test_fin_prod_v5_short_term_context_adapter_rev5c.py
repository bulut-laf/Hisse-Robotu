
from decimal import Decimal
from backend.app.analysis import fin_prod_v5_short_term_context_adapter as m


def test_rev5c_equivalent_aliases_conflict_fail_closed():
    docs = [
        ("a.json", {"technical_trend": "70"}),
        ("b.json", {"technical_trend_score": "71"}),
    ]
    value, evidence = m._extract_exact_metric(
        docs,
        ("technical_trend", "technical_trend_score", "trend_score"),
    )
    assert value is None
    assert evidence["status"] == "CONFLICT"


def test_rev5c_volume_priority_uses_liquidity_without_merging_accumulation():
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
    assert value == Decimal("80")
    assert evidence["key"] == "likidite_puani"


def test_rev5c_same_priority_alias_conflict_still_fails_closed():
    docs = [
        ("a.json", {"likidite_puani": 80}),
        ("b.json", {"likidite_puani": 81}),
    ]
    value, evidence = m._extract_exact_metric(
        docs,
        m._EXACT_KEYS["volume_liquidity"],
    )
    assert value is None
    assert evidence["status"] == "CONFLICT"
    assert evidence["alias"] == "likidite_puani"
