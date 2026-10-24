import json
from pathlib import Path


def test_akbnk_kap_pdf_normalization_text_extraction_contract():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_KAP_PDF_EVIDENCE_NORMALIZATION_TEXT_EXTRACTION.json"
    )

    assert path.exists()

    data = json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )

    assert data[
        "status"
    ] in {
        "PASS",
        "PASS_FAIL_CLOSED",
    }

    assert (
        data[
            "expected_sha256"
        ]
        == "48a89d5e4343ee8b34fd7af9e2c73f6405e25b803b2d1695b4374bcacba9b9e5"
    )

    assert (
        data[
            "source_bytes_mutated"
        ]
        == "NO"
    )

    assert (
        data[
            "bank_metric_mapping_ready"
        ]
        is False
    )

    assert (
        data[
            "scoring_ready"
        ]
        is False
    )

    assert (
        data[
            "activation_ready"
        ]
        is False
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

    if data[
        "financial_text_ready"
    ]:
        assert (
            data["hash_match"]
            is True
        )
        assert (
            data["pdf_magic"]
            is True
        )
        assert (
            data[
                "normalized_copy_written"
            ]
            is True
        )
        assert (
            data["page_count"]
            > 0
        )
        assert (
            data[
                "text_char_count"
            ]
            > 1000
        )
        assert (
            data[
                "metric_family_present_count"
            ]
            >= 5
        )
    else:
        assert len(
            data["blockers"]
        ) > 0
