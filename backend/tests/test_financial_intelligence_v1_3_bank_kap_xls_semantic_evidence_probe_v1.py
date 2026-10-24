import json
from pathlib import Path


def test_bank_kap_xls_semantic_probe_contract():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_BANK_KAP_XLS_SEMANTIC_EVIDENCE_PROBE.json"
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
        data["xls_file_count"],
        int,
    )

    assert isinstance(
        data["kap_parser_pass_count"],
        int,
    )

    assert isinstance(
        data["bank_kap_xls_count"],
        int,
    )

    for row in data[
        "bank_kap_xls"
    ]:
        assert row["symbol"] in {
            "AKBNK",
            "GARAN",
            "HALKB",
            "ISCTR",
            "SKBNK",
            "TSKB",
            "VAKBN",
            "YKBNK",
        }

        assert (
            row["canonical_fact_count"]
            > 0
        )

        assert len(
            row["sha256"]
        ) == 64

    if data[
        "bank_kap_xls_count"
    ] == 0:
        assert (
            data[
                "canonical_producer_ready"
            ]
            is False
        )
        assert (
            data["production_evidence"]
            is False
        )
        assert (
            "NO_PARSEABLE_BANK_KAP_XLS_SOURCE"
            in data["blockers"]
        )
    else:
        assert (
            data[
                "canonical_producer_ready"
            ]
            is True
        )
        assert (
            data["production_evidence"]
            is True
        )

    assert (
        data["activation_ready"]
        is False
    )
    assert data["mutation"] == "NO"
    assert data["store_mutation"] == "NO"
    assert data["al_sat_mutation"] == "NO"
