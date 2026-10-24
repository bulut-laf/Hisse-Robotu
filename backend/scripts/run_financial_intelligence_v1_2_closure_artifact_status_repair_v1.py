from __future__ import annotations

import ast
import json
from datetime import datetime
from pathlib import Path
import shutil


def main():
    root = Path(r"D:\Projects\Hisse-Robotu")

    closure_path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_2_SECTOR_EXPANSION_CLOSURE.json"
    )

    test_path = (
        root
        / "backend"
        / "tests"
        / "test_financial_intelligence_v1_2_sector_expansion_closure_v1.py"
    )

    if not closure_path.exists():
        raise SystemExit("CLOSURE_ARTIFACT_MISSING")

    if not test_path.exists():
        raise SystemExit("CLOSURE_TEST_MISSING")

    closure = json.loads(
        closure_path.read_text(
            encoding="utf-8-sig"
        )
    )

    expected_supported = {
        "INDUSTRIAL",
        "BANK",
        "INSURANCE",
        "REIT",
        "HOLDING",
    }

    if set(
        closure.get("supported_sector_models")
        or []
    ) != expected_supported:
        raise SystemExit(
            "CLOSURE_SUPPORTED_SECTORS_INVALID"
        )

    if list(
        closure.get("production_ready_models")
        or []
    ) != ["INDUSTRIAL"]:
        raise SystemExit(
            "CLOSURE_PRODUCTION_READY_INVALID"
        )

    expected_blockers = {
        "BANK": "NO_REAL_BANK_SOURCE",
        "INSURANCE": "NO_REAL_INSURANCE_SOURCE",
        "REIT": "NO_REAL_REIT_SOURCE",
        "HOLDING": "NO_REAL_HOLDING_SOURCE",
    }

    blocked = closure.get(
        "blocked_production_models"
    ) or {}

    for sector, expected in expected_blockers.items():
        values = blocked.get(sector) or []

        if expected not in values:
            raise SystemExit(
                f"{sector}_BLOCKER_INVALID"
            )

    if closure.get("industrial_threshold_reuse") is not False:
        raise SystemExit(
            "INDUSTRIAL_THRESHOLD_REUSE_INVALID"
        )

    if closure.get("missing_to_zero") is not False:
        raise SystemExit(
            "MISSING_TO_ZERO_INVALID"
        )

    if closure.get("future_publication_allowed") is not False:
        raise SystemExit(
            "FUTURE_PUBLICATION_POLICY_INVALID"
        )

    if closure.get("al_sat_authority") != "NONE":
        raise SystemExit(
            "AL_SAT_AUTHORITY_INVALID"
        )

    backup = (
        root
        / "_backup"
        / (
            "FIN_INTEL_V1_2_CLOSURE_STATUS_REPAIR_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
        )
    )
    backup.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        closure_path,
        backup / closure_path.name,
    )
    shutil.copy2(
        test_path,
        backup / test_path.name,
    )

    closure["status"] = "PASS"

    closure_path.write_text(
        json.dumps(
            closure,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    text = test_path.read_text(
        encoding="utf-8-sig"
    )

    if '"status": "PASS",' not in text:
        anchor = (
            '"schema_version":\n'
            '            "financial-intelligence-v1-2-'
            'sector-expansion-closure-v1",\n'
        )

        replacement = (
            anchor
            + '        "status": "PASS",\n'
        )

        if anchor not in text:
            raise SystemExit(
                "CLOSURE_TEST_STATUS_ANCHOR_NOT_FOUND"
            )

        text = text.replace(
            anchor,
            replacement,
            1,
        )

    ast.parse(text)

    test_path.write_text(
        text,
        encoding="utf-8",
        newline="\n",
    )

    reread = json.loads(
        closure_path.read_text(
            encoding="utf-8-sig"
        )
    )

    if reread.get("status") != "PASS":
        raise SystemExit(
            "CLOSURE_STATUS_REPAIR_FAILED"
        )

    print(f"BACKUP={backup}")
    print(f"CLOSURE_ARTIFACT={closure_path}")
    print(f"CLOSURE_TEST={test_path}")
    print("CLOSURE_STATUS=PASS")
    print("PRODUCTION_READY_MODELS=['INDUSTRIAL']")
    print("SPECIAL_SECTOR_PRODUCTION_ACTIVATION=NO")
    print("STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print(
        "FINANCIAL_INTELLIGENCE_V1_2_"
        "CLOSURE_ARTIFACT_STATUS_REPAIR_V1=PASS"
    )


if __name__ == "__main__":
    main()
