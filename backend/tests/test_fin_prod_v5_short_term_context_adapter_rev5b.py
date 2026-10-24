
from decimal import Decimal
from backend.app.analysis import fin_prod_v5_short_term_context_adapter as m


def test_rev5b_volume_liquidity_uses_existing_alias_priority():
    docs = [(
        "candidate.json",
        {
            "likidite_puani": 81,
            "hacim_birikimi_puani": 77,
        },
    )]

    value, evidence = m._extract_exact_metric(
        docs,
        m._EXACT_KEYS["volume_liquidity"],
    )

    assert value == Decimal("81")
    assert evidence["status"] == "EXACT"
    assert evidence["key"] == "likidite_puani"


def test_rev5b_conflict_only_for_same_exact_alias():
    docs = [
        ("a.json", {"likidite_puani": 81}),
        ("b.json", {"likidite_puani": 82}),
    ]

    value, evidence = m._extract_exact_metric(
        docs,
        m._EXACT_KEYS["volume_liquidity"],
    )

    assert value is None
    assert evidence["status"] == "CONFLICT"
    assert evidence["alias"] == "likidite_puani"
