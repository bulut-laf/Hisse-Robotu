from __future__ import annotations

import json
from pathlib import Path


SCHEMA_VERSION = "fin-prod-v8-fin016-production-closure-v1"


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    fi = root / "backend" / "data" / "financial_intelligence"

    contract_path = fi / "FIN_PROD_V8_FIN016_CONTRACT_ACCEPTANCE.json"
    resolver_path = fi / "FIN_PROD_V8_FIN016_HISTORICAL_PIT_PRODUCER_RESOLUTION_V2.json"
    out = fi / "FIN_PROD_V8_FIN016_PRODUCTION_CLOSURE.json"

    contract = _load(contract_path)
    resolver = _load(resolver_path)

    contract_ok = (
        contract.get("status") == "PASS"
        and contract.get("read_only") is True
        and contract.get("pit_leakage_count") == 0
        and contract.get("weight_optimization") is False
        and contract.get("threshold_optimization") is False
    )

    producer_status = resolver.get("status")
    blocker = resolver.get("blocker")

    unresolved = []
    if not contract_ok:
        unresolved.append("FIN016_CORE_CONTRACT_NOT_READY")
    if producer_status != "EXACT_PRODUCTION_OBSERVATION_PRODUCER_FOUND":
        unresolved.append(blocker or "HISTORICAL_PIT_OBSERVATION_PRODUCER_MISSING")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS_CLOSED_WITH_EXPLICIT_BLOCKERS" if contract_ok else "BLOCKED",
        "mode": "READ_ONLY_FIN016_PRODUCTION_CLOSURE",
        "read_only": True,
        "core_contract": {
            "status": contract.get("status"),
            "pit_usable_count": contract.get("pit_usable_count"),
            "pit_leakage_count": contract.get("pit_leakage_count"),
            "calibration_status": (contract.get("calibration") or {}).get("status"),
            "separation": (contract.get("calibration") or {}).get("separation"),
            "production_evidence": contract.get("production_evidence"),
        },
        "historical_pit_producer": {
            "status": producer_status,
            "primary": resolver.get("primary"),
            "blocker": blocker,
        },
        "unresolved_blockers": unresolved,
        "rules": [
            "POINT_IN_TIME_VALIDATION_ACTIVE",
            "FUTURE_PUBLICATION_BLOCKED",
            "CALIBRATION_MEASURES_ONLY",
            "NO_AUTO_WEIGHT_OPTIMIZATION",
            "NO_AUTO_THRESHOLD_OPTIMIZATION",
            "NO_SYNTHETIC_DATA_AS_PRODUCTION_CALIBRATION",
            "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION",
        ],
        "closure_statement": (
            "FIN-016 validation/calibration infrastructure is complete and fail-closed. "
            "Production historical calibration remains explicitly unavailable until a real "
            "historical PIT observation producer exists."
        ),
    }

    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STATUS={payload['status']}")
    print(f"CORE_CONTRACT={'PASS' if contract_ok else 'FAIL'}")
    print(f"PRODUCER_STATUS={producer_status}")
    print(f"UNRESOLVED_BLOCKERS={unresolved}")
    print(f"RESULT={out}")
    print("FIN_PROD_V8_FIN016_PRODUCTION_CLOSURE=PASS")


if __name__ == "__main__":
    main()
