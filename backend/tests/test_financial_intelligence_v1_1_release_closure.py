import json
from pathlib import Path


def test_financial_intelligence_v1_1_release_closure():

    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_1_RELEASE_CLOSURE.json"
    )

    assert path.exists()

    data = json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )

    assert (
        data["status"]
        == "READY_FOR_V1_1_RELEASE_WITH_KNOWN_LIMITATIONS"
    )

    assert data["reference_symbol"] == "TUPRS"

    assert data["symbol_count"] == 1

    assert data["release_ready_symbols"] == [
        "TUPRS"
    ]

    assert data["release_blockers"] == []

    assert (
        "NO_ADDITIONAL_ACCEPTED_SYMBOLS_FOUND"
        in data["known_limitations"]
    )

    assert (
        "NO_SYNTHETIC_SYMBOLS"
        in data["rules"]
    )

    assert (
        "NO_DASHBOARD_ROUTE_MUTATION"
        in data["rules"]
    )
