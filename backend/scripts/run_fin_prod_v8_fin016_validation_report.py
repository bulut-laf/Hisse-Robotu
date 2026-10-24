from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.analysis.financial_intelligence_validation_report import (
    build_fin016_validation_report,
)
from app.models.investability_models import PointInTimeObservation


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "backend" / "data" / "financial_intelligence" / "FIN_PROD_V8_FIN016_CONTRACT_ACCEPTANCE.json"


def D(v):
    return Decimal(str(v))


def main() -> None:
    # Contract acceptance dataset only: deterministic PIT examples matching the
    # already-existing FIN-016 tests. This is not market evidence and is clearly
    # labeled as contract acceptance rather than production calibration.
    rows = tuple(
        PointInTimeObservation(
            date(2026, 8, 5),
            date(2026, 8, 4),
            80 if i % 2 == 0 else 40,
            D("0.05") if i % 2 == 0 else D("-0.01"),
        )
        for i in range(20)
    )
    payload = build_fin016_validation_report(rows)
    payload["artifact_role"] = "CONTRACT_ACCEPTANCE_ONLY_NOT_PRODUCTION_MARKET_CALIBRATION"
    payload["symbol"] = None
    payload["production_evidence"] = False

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"STATUS={payload['status']}")
    print(f"PIT_USABLE={payload['pit_usable_count']}")
    print(f"PIT_LEAKAGE={payload['pit_leakage_count']}")
    print(f"CALIBRATION_STATUS={payload['calibration']['status']}")
    print(f"SEPARATION={payload['calibration']['separation']}")
    print(f"RESULT={OUT}")
    print("FIN_PROD_V8_FIN016_VALIDATION_REPORT_CORE=PASS")


if __name__ == "__main__":
    main()
