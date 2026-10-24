from __future__ import annotations

import json
from pathlib import Path

EXPECTED_BLOCKER = "OBSERVATION_DATE_MARKET_PRICE_MISSING:TUPRS"

def main():
    root = Path(__file__).resolve().parents[2]
    fi = root / "backend" / "data" / "financial_intelligence"

    source = fi / "FIN_PROD_V9_HISTORICAL_PIT_PRODUCTION_OBSERVATIONS.json"

    if not source.exists():
        raise FileNotFoundError(source)

    data = json.loads(source.read_text(encoding="utf-8-sig"))

    blockers = list(data.get("blockers") or [])

    checks = {
        "producer_read_only":
            data.get("mode") == "READ_ONLY_PRODUCTION_PIT_OBSERVATION_PRODUCER",

        "observation_count_zero":
            data.get("observation_count") == 0,

        "producer_status_correct":
            data.get("status") == "NO_PRODUCTION_OBSERVATIONS",

        "exact_market_blocker":
            EXPECTED_BLOCKER in blockers,

        "synthetic_calibration_forbidden":
            "NO_SYNTHETIC_PRODUCTION_CALIBRATION"
            in (data.get("rules") or []),
    }

    failed = [name for name, ok in checks.items() if not ok]

    status = (
        "PASS_CLOSED_WITH_EXPLICIT_BLOCKER"
        if not failed
        else "BLOCKED"
    )

    payload = {
        "schema_version":
            "fin-prod-v9-historical-pit-closure-v1",

        "status":
            status,

        "producer_status":
            data.get("status"),

        "observation_count":
            data.get("observation_count"),

        "calibration_status":
            (data.get("calibration") or {}).get("status"),

        "calibration_separation":
            (data.get("calibration") or {}).get("separation"),

        "closed_with_blocker":
            EXPECTED_BLOCKER if not failed else None,

        "remaining_limitation":
            "HISTORICAL_PIT_OBSERVATION_PRODUCER_MARKET_HISTORY_GAP",

        "checks":
            checks,

        "failed_checks":
            failed,

        "rules": [
            "NO_SYNTHETIC_PRODUCTION_CALIBRATION",
            "NO_FUZZY_MARKET_DATE_MAPPING",
            "NO_FILE_MTIME_AS_MARKET_DATE",
            "NO_OBSERVATION_DATE_SUBSTITUTION",
            "NO_WEIGHT_OPTIMIZATION",
            "NO_THRESHOLD_OPTIMIZATION",
            "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION",
        ],
    }

    output = fi / "FIN_PROD_V9_HISTORICAL_PIT_CLOSURE.json"

    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"STATUS={status}")
    print(f"PRODUCER_STATUS={payload['producer_status']}")
    print(f"OBSERVATION_COUNT={payload['observation_count']}")
    print(f"CALIBRATION_STATUS={payload['calibration_status']}")
    print(f"CLOSED_WITH_BLOCKER={payload['closed_with_blocker']}")
    print(f"REMAINING_LIMITATION={payload['remaining_limitation']}")
    print(f"RESULT={output}")

    if status != "PASS_CLOSED_WITH_EXPLICIT_BLOCKER":
        raise SystemExit(
            "FIN_PROD_V9_HISTORICAL_PIT_CLOSURE=FAILED"
        )

    print("FIN_PROD_V9_HISTORICAL_PIT_CLOSURE=PASS")

if __name__ == "__main__":
    main()
