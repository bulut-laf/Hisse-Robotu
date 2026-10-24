import json
from pathlib import Path


def test_bank_official_kap_financial_preflight_contract():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_BANK_OFFICIAL_KAP_FINANCIAL_ACQUISITION_PREFLIGHT.json"
    )

    assert path.exists()

    data = json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )

    assert data["status"] in {
        "PASS",
        "PASS_FAIL_CLOSED",
    }

    assert isinstance(
        data[
            "candidate_source_file_count"
        ],
        int,
    )

    assert isinstance(
        data[
            "candidate_definition_count"
        ],
        int,
    )

    assert isinstance(
        data[
            "top_source_files"
        ],
        list,
    )

    for row in data[
        "top_source_files"
    ]:
        path_text = row[
            "path"
        ].lower()

        assert "\\backend\\data\\" not in path_text
        assert "\\backend\\cache\\" not in path_text
        assert "\\data\\" not in path_text or "\\backend\\app\\" in path_text or "\\backend\\scripts\\" in path_text

    assert (
        data[
            "bank_activation_ready"
        ]
        is False
    )

    assert (
        data[
            "production_mutation"
        ]
        == "NO"
    )

    assert (
        data[
            "store_mutation"
        ]
        == "NO"
    )

    assert (
        data[
            "al_sat_mutation"
        ]
        == "NO"
    )
