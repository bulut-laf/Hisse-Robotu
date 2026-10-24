from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


OLD_LIMITATION = "HISTORICAL_PIT_OBSERVATION_PRODUCER_MISSING"
NEW_LIMITATION = "HISTORICAL_PIT_OBSERVATION_PRODUCER_MARKET_HISTORY_GAP"
EXPECTED_V9_STATUS = "PASS_CLOSED_WITH_EXPLICIT_BLOCKER"
EXPECTED_V9_BLOCKER = "OBSERVATION_DATE_MARKET_PRICE_MISSING:TUPRS"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    fi = root / "backend" / "data" / "financial_intelligence"

    manifest_path = fi / "FINANCIAL_INTELLIGENCE_V1_RELEASE_MANIFEST.json"
    v9_path = fi / "FIN_PROD_V9_HISTORICAL_PIT_CLOSURE.json"

    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    if not v9_path.exists():
        raise FileNotFoundError(v9_path)

    manifest = _load(manifest_path)
    v9 = _load(v9_path)

    if v9.get("status") != EXPECTED_V9_STATUS:
        raise RuntimeError(f"V9_STATUS_NOT_CLOSED:{v9.get('status')}")
    if v9.get("closed_with_blocker") != EXPECTED_V9_BLOCKER:
        raise RuntimeError(
            f"V9_BLOCKER_MISMATCH:{v9.get('closed_with_blocker')}"
        )

    known = list(manifest.get("KNOWN_LIMITATIONS") or manifest.get("known_limitations") or [])
    known = [x for x in known if x != OLD_LIMITATION]
    if NEW_LIMITATION not in known:
        known.append(NEW_LIMITATION)

    # Preserve existing manifest contract while adding an explicit reconciliation block.
    manifest["KNOWN_LIMITATIONS"] = known
    manifest["FIN016_PRODUCTION_STATUS"] = "CLOSED_WITH_EXPLICIT_BLOCKER"
    manifest["FIN016_PRODUCTION_CALIBRATION_READY"] = False
    manifest["FIN016_PRODUCTION_OBSERVATION_COUNT"] = int(v9.get("observation_count") or 0)
    manifest["FIN016_EXACT_BLOCKER"] = EXPECTED_V9_BLOCKER
    manifest["FIN016_REMAINING_LIMITATION"] = NEW_LIMITATION
    manifest["FIN016_SYNTHETIC_CALIBRATION_FORBIDDEN"] = True
    manifest["V9_CLOSURE_ARTIFACT"] = str(v9_path)
    manifest["MANIFEST_SYNCED_AT_UTC"] = datetime.now(timezone.utc).isoformat()

    # Release readiness remains valid because this limitation is already non-release-blocking.
    blockers = list(manifest.get("RELEASE_BLOCKERS") or manifest.get("release_blockers") or [])
    blockers = [x for x in blockers if x != OLD_LIMITATION and x != NEW_LIMITATION]
    manifest["RELEASE_BLOCKERS"] = blockers

    status = manifest.get("STATUS") or manifest.get("status")
    if status != "READY_FOR_V1_RELEASE_WITH_KNOWN_LIMITATIONS":
        raise RuntimeError(f"UNEXPECTED_RELEASE_STATUS:{status}")

    out = manifest_path
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STATUS={status}")
    print(f"FIN016_PRODUCTION_STATUS={manifest['FIN016_PRODUCTION_STATUS']}")
    print(f"FIN016_PRODUCTION_CALIBRATION_READY={manifest['FIN016_PRODUCTION_CALIBRATION_READY']}")
    print(f"FIN016_PRODUCTION_OBSERVATION_COUNT={manifest['FIN016_PRODUCTION_OBSERVATION_COUNT']}")
    print(f"FIN016_EXACT_BLOCKER={manifest['FIN016_EXACT_BLOCKER']}")
    print(f"KNOWN_LIMITATIONS={manifest['KNOWN_LIMITATIONS']}")
    print(f"RELEASE_BLOCKERS={manifest['RELEASE_BLOCKERS']}")
    print(f"RESULT={out}")
    print("FINANCIAL_INTELLIGENCE_V1_RELEASE_MANIFEST_SYNC_V2=PASS")


if __name__ == "__main__":
    main()
