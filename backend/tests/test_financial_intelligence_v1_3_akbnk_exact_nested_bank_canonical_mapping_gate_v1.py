import json
from pathlib import Path


def test_akbnk_exact_nested_bank_canonical_mapping_gate():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_EXACT_NESTED_BANK_CANONICAL_MAPPING_GATE.json"
    )

    assert path.exists()

    data = json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )

    assert data["symbol"] == "AKBNK"
    assert data["sector_model"] == "BANK"

    nested = data[
        "nested_canonical_facts"
    ]

    assert (
        nested[
            "CAPITAL_ADEQUACY"
        ][
            "capital_adequacy_ratio"
        ]
        == "16.38"
    )

    assert (
        "deposit_growth"
        in nested[
            "GROWTH_QUALITY"
        ]
    )

    assert (
        "net_income_growth"
        in nested[
            "GROWTH_QUALITY"
        ]
    )

    assert data[
        "missing_to_zero"
    ] is False

    assert data[
        "industrial_threshold_reuse"
    ] is False

    assert data[
        "scoring_ready"
    ] is False

    assert data[
        "activation_ready"
    ] is False

    assert data[
        "production_mutation"
    ] == "NO"

    assert data[
        "store_mutation"
    ] == "NO"

    assert data[
        "al_sat_mutation"
    ] == "NO"
