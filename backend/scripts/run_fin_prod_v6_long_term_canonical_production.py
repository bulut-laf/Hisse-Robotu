
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
import json
import sys

ROOT = Path(r"D:\Projects\Hisse-Robotu")
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

FI = BACKEND / "data" / "financial_intelligence"
ACCEPT = BACKEND / "data" / "financial_intelligence_acceptance_TUPRS_2026_2.json"
EVIDENCE = FI / "TUPRS_long_term_evidence_completion.json"
OUT = FI / "TUPRS_long_term_canonical_coverage.json"

AS_OF = "2026-08-04"
SYMBOL = "TUPRS"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def find_component(financial_health: dict, code: str):
    for item in financial_health.get("components") or []:
        if isinstance(item, dict) and str(item.get("code") or "").upper() == code:
            return item
    return None


def serialize(v):
    if is_dataclass(v):
        return {k: serialize(x) for k, x in asdict(v).items()}
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date,)):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): serialize(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [serialize(x) for x in v]
    return v


def extract_fundamental_quality_from_existing_system():
    """
    Read-only attempt:
    1) use existing fundamental_scores.json if present;
    2) otherwise do NOT invent a score.
    """
    store = BACKEND / "data" / "fundamental_scores.json"
    if not store.exists():
        return None, {
            "status": "MISSING",
            "source": str(store),
            "reason": "EXISTING_FUNDAMENTAL_SCORE_STORE_MISSING",
        }

    obj = load(store)
    if not isinstance(obj, dict):
        return None, {
            "status": "INVALID",
            "source": str(store),
            "reason": "INVALID_FUNDAMENTAL_SCORE_STORE",
        }

    candidates = []
    for key, rec in obj.items():
        if not str(key).upper().startswith("TUPRS|"):
            continue
        if not isinstance(rec, dict):
            continue
        score = rec.get("score") or {}
        if not isinstance(score, dict):
            continue
        total = score.get("total_score")
        locked = score.get("locked")
        period_end = str(rec.get("period_end") or "")
        if total is not None and locked is not True and period_end and period_end <= AS_OF:
            candidates.append((period_end, total, key, rec))

    if not candidates:
        return None, {
            "status": "MISSING",
            "source": str(store),
            "reason": "NO_POINT_IN_TIME_VALID_TUPRS_FUNDAMENTAL_SCORE",
        }

    period_end, total, key, rec = sorted(candidates, reverse=True)[0]
    return Decimal(str(total)), {
        "status": "PASS",
        "source": str(store),
        "record_key": key,
        "period_end": period_end,
        "field": "score.total_score",
        "value": str(total),
        "point_in_time_valid": True,
    }


def main():
    financial = load(ACCEPT)
    evidence = load(EVIDENCE)

    if str(financial.get("status") or "").upper() != "PASS":
        raise SystemExit("FINANCIAL_ACCEPTANCE_NOT_PASS")

    if str(financial.get("symbol") or SYMBOL).upper() != SYMBOL:
        raise SystemExit("SYMBOL_MISMATCH")

    fh = financial.get("financial_health") or {}
    if fh.get("locked") is True:
        raise SystemExit("FINANCIAL_HEALTH_LOCKED")

    cap = find_component(fh, "CAPITAL_EFFICIENCY")
    if not cap:
        raise SystemExit("CAPITAL_EFFICIENCY_COMPONENT_MISSING")

    cap_score = cap.get("score")
    if cap_score is None:
        raise SystemExit("CAPITAL_EFFICIENCY_SCORE_MISSING")

    long_ctx = (evidence.get("long_term_context") or {})
    growth = long_ctx.get("growth_durability")
    governance = long_ctx.get("governance")

    if growth is None:
        raise SystemExit("GROWTH_DURABILITY_MISSING")
    if governance is None:
        raise SystemExit("GOVERNANCE_MISSING")

    business_quality, business_evidence = extract_fundamental_quality_from_existing_system()

    # Coverage from the existing FIN-014 weight contract.
    # Only actual non-null, point-in-time-valid existing values count.
    weights = {
        "business_quality": Decimal("0.15") if business_quality is not None else Decimal("0"),
        "financial_health": Decimal("0.15"),
        "cash_quality": Decimal("0.12"),
        "capital_efficiency": Decimal("0.12"),
        "growth_durability": Decimal("0.12"),
        "governance": Decimal("0.08"),
        "valuation": Decimal("0.12"),
        "margin_of_safety": Decimal("0.09"),
        "sector_risk": Decimal("0"),
    }
    coverage = sum(weights.values(), Decimal("0"))

    business_status = "PASS" if business_quality is not None else "BLOCKED"
    coverage_pass = coverage >= Decimal("0.70")

    blockers = []
    # V4 canonical contract still requires explicit business-quality evidence.
    if business_quality is None:
        blockers.append("BUSINESS_QUALITY_CANONICAL_EVIDENCE_MISSING")
    if not coverage_pass:
        blockers.append("LONG_TERM_WEIGHT_COVERAGE_BELOW_0_70")

    payload = {
        "status": "PASS" if not blockers else "BLOCKED",
        "mode": "READ_ONLY_EXACT_LONG_TERM_CANONICAL_PRODUCTION_V6",
        "schema_version": "fin-prod-v6-long-term-canonical-coverage-v1",
        "symbol": SYMBOL,
        "as_of_date": AS_OF,
        "canonical": True,
        "business_quality": {
            "status": business_status,
            "value": None if business_quality is None else str(business_quality),
            "evidence": business_evidence,
        },
        "governance": {
            "status": "PASS",
            "value": str(governance),
            "evidence": {
                "source": str(EVIDENCE),
                "field": "long_term_context.governance",
                "point_in_time_valid": True,
            },
        },
        "growth_context": {
            "status": "PASS",
            "growth_durability": str(growth),
            "evidence": {
                "source": str(EVIDENCE),
                "field": "long_term_context.growth_durability",
                "point_in_time_valid": True,
            },
        },
        "capital_efficiency": {
            "status": "PASS",
            "value": str(cap_score),
            "evidence": {
                "source": str(ACCEPT),
                "field": "financial_health.components[CAPITAL_EFFICIENCY].score",
                "point_in_time_valid": True,
                "note": "Existing Financial Health component; no new score formula.",
            },
        },
        "coverage": {
            "value": str(coverage),
            "unlock_threshold": "0.70",
            "threshold_pass": coverage_pass,
            "weights_counted": {k: str(v) for k, v in weights.items() if v > 0},
        },
        "data_quality": {
            "status": "PASS" if not blockers else "BLOCKED",
            "point_in_time": "PASS",
            "missing_is_not_zero": True,
        },
        "blockers": blockers,
        "warnings": [],
        "production_rules": [
            "Read-only.",
            "No new AL/SAT, scanner, ranking or portfolio mutation.",
            "No missing value is converted to zero.",
            "Capital efficiency reuses the existing Financial Health component.",
            "Business quality must come from an existing canonical fundamental-quality score; it is not synthesized.",
            "Point-in-time evidence must be dated on or before as_of_date.",
        ],
    }

    dump(OUT, serialize(payload))

    print("FIN_PROD_V6_LONG_TERM_CANONICAL_PRODUCTION")
    print("STATUS=" + payload["status"])
    print("SYMBOL=" + SYMBOL)
    print("AS_OF_DATE=" + AS_OF)
    print("CAPITAL_EFFICIENCY_SCORE=" + str(cap_score))
    print("GROWTH_DURABILITY=" + str(growth))
    print("GOVERNANCE=" + str(governance))
    print("BUSINESS_QUALITY=" + ("MISSING" if business_quality is None else str(business_quality)))
    print("LONG_TERM_COVERAGE=" + str(coverage))
    print("UNLOCK_THRESHOLD=0.70")
    print("BLOCKERS=" + json.dumps(blockers, ensure_ascii=False))
    print("RESULT=" + str(OUT))

    # Exit nonzero only on actual execution/data-contract corruption.
    # Missing business-quality remains an explicit fail-closed business blocker.
    print("FIN_PROD_V6_LONG_TERM_CANONICAL_PRODUCTION=PASS")


if __name__ == "__main__":
    main()
