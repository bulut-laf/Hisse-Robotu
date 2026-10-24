import json
from decimal import Decimal
from pathlib import Path


def test_akbnk_exact_numeric_bank_metric_extraction_contract():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_EXACT_NUMERIC_BANK_METRIC_EXTRACTION_CANONICAL_GATE.json"
    )

    assert path.exists()

    data = json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )

    assert data["symbol"] == "AKBNK"
    assert data["sector_model"] == "BANK"
    assert data["source_type"] == "KAP"

    assert data["hash_verified"] is True

    assert data["missing_to_zero"] is False

    assert (
        data[
            "future_publication_allowed"
        ]
        is False
    )

    assert (
        data["scoring_ready"]
        is False
    )

    assert (
        data["activation_ready"]
        is False
    )

    assert (
        data["production_mutation"]
        == "NO"
    )

    assert (
        data["store_mutation"]
        == "NO"
    )

    assert (
        data["al_sat_mutation"]
        == "NO"
    )

    capital = data[
        "metrics"
    ][
        "capital_adequacy_ratio"
    ]

    if capital is not None:
        assert Decimal(
            capital
        ) > Decimal("0")

    for metric in (
        "net_interest_margin",
        "roe",
    ):
        if metric in data[
            "guidance_rejections"
        ]:
            assert (
                data["metrics"][metric]
                is None
            )
