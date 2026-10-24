import json
from pathlib import Path


def test_akbnk_pdf_signature_offset_repair():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_KAP_PDF_SIGNATURE_OFFSET_REPAIR.json"
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

    assert data["hash_match"] is True

    assert (
        data["actual_sha256"]
        == data["expected_sha256"]
    )

    assert (
        data["normalized_copy_written"]
        is True
    )

    assert (
        data["normalized_sha256"]
        == data["actual_sha256"]
    )

    assert (
        data["source_bytes_mutated"]
        == "NO"
    )

    assert (
        data["bank_metric_mapping_ready"]
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
        data["store_mutation"]
        == "NO"
    )
    assert (
        data["al_sat_mutation"]
        == "NO"
    )

    if data["financial_text_ready"]:
        assert (
            data["page_count"]
            > 0
        )
        assert (
            data["text_char_count"]
            > 1000
        )
        assert (
            data[
                "financial_term_present_count"
            ]
            >= 3
        )
    else:
        assert len(
            data["blockers"]
        ) > 0
