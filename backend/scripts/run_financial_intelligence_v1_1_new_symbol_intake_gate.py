from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9]{2,7}$")
SECTOR_MODELS = {"INDUSTRIAL", "BANK", "INSURANCE", "REIT", "HOLDING"}
SUPPORTED_EXT = {".xls", ".xlsx", ".json"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=r"D:\Projects\Hisse-Robotu")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--sector-model", required=True)
    ap.add_argument("--source-file", required=True)
    ap.add_argument("--period", required=True, help="Canonical period identity, e.g. 2026_2")
    args = ap.parse_args()

    root = Path(args.project_root)
    backend = root / "backend"
    fi_dir = backend / "data" / "financial_intelligence"

    symbol = args.symbol.strip().upper()
    sector_model = args.sector_model.strip().upper()
    source = Path(args.source_file)
    period = args.period.strip()

    blockers = []

    if not SYMBOL_RE.fullmatch(symbol):
        blockers.append("INVALID_SYMBOL")

    if sector_model not in SECTOR_MODELS:
        blockers.append("UNKNOWN_SECTOR_MODEL")

    if not source.exists():
        blockers.append("SOURCE_FILE_MISSING")
    elif source.suffix.lower() not in SUPPORTED_EXT:
        blockers.append("UNSUPPORTED_SOURCE_FILE_TYPE")

    if not re.fullmatch(r"\d{4}_[A-Za-z0-9-]+", period):
        blockers.append("INVALID_PERIOD_IDENTITY")

    # V1 production model contract: non-industrial sectors cannot silently
    # reuse INDUSTRIAL thresholds. Intake may identify them, but rollout
    # remains blocked until their dedicated model is explicitly supported.
    dedicated_model_ready = sector_model == "INDUSTRIAL"
    if sector_model in {"BANK", "INSURANCE", "REIT", "HOLDING"}:
        blockers.append(f"DEDICATED_{sector_model}_MODEL_REQUIRED")

    existing_acceptance = (
        backend / "data" / f"financial_intelligence_acceptance_{symbol}_{period}.json"
    )
    existing_acceptance_found = existing_acceptance.exists()

    status = "READY_FOR_CANONICAL_ACCEPTANCE_IMPORT" if not blockers else "BLOCKED"

    payload = {
        "schema_version": "financial-intelligence-v1.1-new-symbol-intake-gate-v1",
        "status": status,
        "mode": "READ_ONLY_INTAKE_GATE",
        "symbol": symbol,
        "sector_model": sector_model,
        "period": period,
        "source_file": str(source),
        "source_exists": source.exists(),
        "source_extension": source.suffix.lower(),
        "dedicated_model_ready": dedicated_model_ready,
        "existing_acceptance_path": str(existing_acceptance),
        "existing_acceptance_found": existing_acceptance_found,
        "blockers": blockers,
        "next_stage": (
            "FIN001_CANONICAL_ACCEPTANCE_IMPORT"
            if status == "READY_FOR_CANONICAL_ACCEPTANCE_IMPORT"
            else None
        ),
        "rules": [
            "REAL_SOURCE_FILE_REQUIRED",
            "EXPLICIT_SYMBOL_REQUIRED",
            "EXPLICIT_PERIOD_REQUIRED",
            "EXPLICIT_SECTOR_MODEL_REQUIRED",
            "NON_INDUSTRIAL_MUST_NOT_USE_INDUSTRIAL_THRESHOLDS",
            "NO_SYNTHETIC_ACCEPTANCE",
            "NO_NEW_SCORE",
            "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION",
        ],
    }

    out = fi_dir / f"{symbol}_new_symbol_intake_gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STATUS={status}")
    print(f"SYMBOL={symbol}")
    print(f"SECTOR_MODEL={sector_model}")
    print(f"PERIOD={period}")
    print(f"SOURCE_EXISTS={source.exists()}")
    print(f"EXISTING_ACCEPTANCE_FOUND={existing_acceptance_found}")
    print(f"BLOCKERS={blockers}")
    print(f"NEXT_STAGE={payload['next_stage']}")
    print(f"RESULT={out}")
    print("FINANCIAL_INTELLIGENCE_V1_1_NEW_SYMBOL_INTAKE_GATE=PASS")


if __name__ == "__main__":
    main()
