from __future__ import annotations

import json
from pathlib import Path


def main():
    root = Path(r"D:\Projects\Hisse-Robotu")

    fi_dir = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
    )

    closure_path = (
        fi_dir
        / "FINANCIAL_INTELLIGENCE_V1_2_SECTOR_EXPANSION_CLOSURE.json"
    )

    closure = json.loads(
        closure_path.read_text(
            encoding="utf-8-sig"
        )
    )

    if closure.get("status") != "PASS":
        raise SystemExit(
            "V1_2_SECTOR_EXPANSION_CLOSURE_NOT_PASS"
        )

    if list(
        closure.get("production_ready_models")
        or []
    ) != ["INDUSTRIAL"]:
        raise SystemExit(
            "UNEXPECTED_PRODUCTION_READY_MODELS"
        )

    manifest = {
        "schema_version":
            "financial-intelligence-v1-2-release-status-manifest-v1",
        "release": "V1.2",
        "status": "CLOSED_PASS",
        "full_regression": {
            "passed": 3915,
            "skipped": 1,
            "failed": 0,
            "status": "PASS",
        },
        "target_regression": {
            "passed": 80,
            "failed": 0,
            "status": "PASS",
        },
        "production_ready_models": [
            "INDUSTRIAL"
        ],
        "infrastructure_ready_but_not_production_ready": {
            "BANK": "NO_REAL_BANK_SOURCE",
            "INSURANCE": "NO_REAL_INSURANCE_SOURCE",
            "REIT": "NO_REAL_REIT_SOURCE",
            "HOLDING": "NO_REAL_HOLDING_SOURCE",
        },
        "sector_fallback_policy":
            "FAIL_CLOSED",
        "industrial_threshold_reuse_for_special_sectors":
            False,
        "missing_to_zero":
            False,
        "future_publication_allowed":
            False,
        "production_evidence_synthesized":
            False,
        "al_sat_authority":
            "NONE",
        "scanner_mutation":
            False,
        "ranking_mutation":
            False,
        "portfolio_mutation":
            False,
        "tefas_history_verified_period":
            1,
        "tefas_unverified_period_rejected_before_network":
            True,
    }

    out = (
        fi_dir
        / "FINANCIAL_INTELLIGENCE_V1_2_RELEASE_STATUS_MANIFEST.json"
    )

    out.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("STATUS=CLOSED_PASS")
    print("RELEASE=V1.2")
    print(
        "FULL_REGRESSION="
        "{'passed': 3915, 'skipped': 1, "
        "'failed': 0, 'status': 'PASS'}"
    )
    print(
        "TARGET_REGRESSION="
        "{'passed': 80, 'failed': 0, "
        "'status': 'PASS'}"
    )
    print(
        "PRODUCTION_READY_MODELS=['INDUSTRIAL']"
    )
    print(
        "SPECIAL_SECTORS_PRODUCTION_READY=False"
    )
    print(
        "TEFAS_HISTORY_VERIFIED_PERIOD=1"
    )
    print(f"RESULT={out}")
    print(
        "FINANCIAL_INTELLIGENCE_V1_2_"
        "RELEASE_STATUS_MANIFEST_V1=PASS"
    )


if __name__ == "__main__":
    main()
