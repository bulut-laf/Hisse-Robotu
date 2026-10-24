from __future__ import annotations

import json
from pathlib import Path

from app.analysis.financial_intelligence_sector_model_registry import (
    SUPPORTED_SECTOR_MODELS,
    PRODUCTION_READY_MODELS,
)


def main():
    root = Path(__file__).resolve().parents[2]

    fi_dir = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
    )

    sector_files = {
        "BANK":
            "FINANCIAL_INTELLIGENCE_V1_2_BANK_REAL_DATA_INTAKE_GATE.json",
        "INSURANCE":
            "FINANCIAL_INTELLIGENCE_V1_2_INSURANCE_REAL_DATA_INTAKE_GATE.json",
        "REIT":
            "FINANCIAL_INTELLIGENCE_V1_2_REIT_REAL_DATA_INTAKE_GATE.json",
        "HOLDING":
            "FINANCIAL_INTELLIGENCE_V1_2_HOLDING_REAL_DATA_INTAKE_GATE.json",
    }

    blockers = {}
    production_evidence = {}

    for sector, filename in sector_files.items():
        path = fi_dir / filename

        if not path.exists():
            raise SystemExit(
                f"{sector}_REAL_DATA_GATE_ARTIFACT_MISSING"
            )

        data = json.loads(
            path.read_text(
                encoding="utf-8-sig"
            )
        )

        blockers[sector] = list(
            data.get("blockers") or []
        )

        production_evidence[sector] = bool(
            data.get("production_evidence")
        )

        if production_evidence[sector]:
            raise SystemExit(
                f"{sector}_UNEXPECTED_PRODUCTION_EVIDENCE"
            )

    manifest = {
        "schema_version":
            "financial-intelligence-v1-2-sector-expansion-closure-v1",
        "status": "PASS",
        "supported_sector_models":
            list(SUPPORTED_SECTOR_MODELS),
        "production_ready_models":
            list(PRODUCTION_READY_MODELS),
        "blocked_production_models":
            blockers,
        "production_evidence":
            production_evidence,
        "industrial_threshold_reuse": False,
        "missing_to_zero": False,
        "future_publication_allowed": False,
        "al_sat_authority": "NONE",
        "scanner_mutation": False,
        "ranking_mutation": False,
        "portfolio_mutation": False,
    }

    out = (
        fi_dir
        / "FINANCIAL_INTELLIGENCE_V1_2_SECTOR_EXPANSION_CLOSURE.json"
    )

    out.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"STATUS={manifest['status']}")
    print(
        f"SUPPORTED_SECTOR_MODELS="
        f"{manifest['supported_sector_models']}"
    )
    print(
        f"PRODUCTION_READY_MODELS="
        f"{manifest['production_ready_models']}"
    )
    print(
        f"BLOCKED_PRODUCTION_MODELS="
        f"{manifest['blocked_production_models']}"
    )
    print(
        f"PRODUCTION_EVIDENCE="
        f"{manifest['production_evidence']}"
    )
    print(
        "INDUSTRIAL_THRESHOLD_REUSE=False"
    )
    print(
        "MISSING_TO_ZERO=False"
    )
    print(
        "FUTURE_PUBLICATION_ALLOWED=False"
    )
    print(
        "AL_SAT_AUTHORITY=NONE"
    )
    print(
        f"RESULT={out}"
    )
    print(
        "FINANCIAL_INTELLIGENCE_V1_2_"
        "SECTOR_EXPANSION_CLOSURE_V1=PASS"
    )


if __name__ == "__main__":
    main()
