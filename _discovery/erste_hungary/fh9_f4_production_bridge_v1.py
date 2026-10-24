from __future__ import annotations

from collections import Counter
from decimal import Decimal
from pathlib import Path
import json
import os
import re

ROOT = Path(__file__).resolve().parents[2]
DISC = ROOT / "_discovery" / "erste_hungary"

# IMPORTANT:
# F1-F3 are consumed from the already validated baseline evidence.
# They are NOT recomputed here. F4 is the only newly added family.
EVIDENCE = DISC / "f1_f2_f3_evidence_v1_latest.json"
F4 = DISC / "fh9_bamosz_turnover_progress_v11.jsonl"

OUTPUT = DISC / "f1_f2_f3_f4_evidence_v1_latest.json"
SUMMARY = DISC / "f1_f2_f3_f4_evidence_v1_summary_latest.json"

VALID_STATES = {"POSITIVE", "CAUTION", "NEUTRAL"}
BRIDGE_VERSION = "erste-hungary-f4-evidence-bridge-v1"


def norm_isin(value):
    s = str(value or "").upper().strip()
    m = re.search(r"([A-Z]{2}[A-Z0-9]{10})", s)
    return m.group(1) if m else re.sub(r"[^A-Z0-9]", "", s)


def normalize_state(value):
    s = str(value or "").strip().upper()
    if s.startswith("EVIDENCESTATE."):
        s = s.split(".", 1)[1]
    return s


def load_jsonl(path):
    out = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        isin = norm_isin(obj.get("isin"))
        if isin:
            out[isin] = obj
    return out


def classify(states, category_id):
    available = sum(
        1 for family in ("F1", "F2", "F3", "F4")
        if states.get(family) in VALID_STATES
    )
    positive = sum(
        1 for family in ("F1", "F2", "F3", "F4")
        if states.get(family) == "POSITIVE"
    )
    caution = sum(
        1 for family in ("F1", "F2", "F3", "F4")
        if states.get(family) == "CAUTION"
    )

    if not category_id:
        return "X"
    if available < 3:
        return "X"
    if caution >= 2 or (
        states.get("F1") == "CAUTION"
        and states.get("F2") == "CAUTION"
    ):
        return "D"
    if (
        available >= 4
        and positive >= 4
        and (
            states.get("F1") == "POSITIVE"
            or states.get("F2") == "POSITIVE"
        )
        and caution == 0
    ):
        return "A"
    if available >= 3 and positive >= 2 and caution <= 1:
        return "B"
    return "C"


def main():
    if not EVIDENCE.exists():
        raise SystemExit("F4_BASELINE_EVIDENCE_MISSING")
    if not F4.exists():
        raise SystemExit("F4_BAMOSZ_CACHE_MISSING")

    baseline = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if not isinstance(baseline, list):
        raise SystemExit("F4_BASELINE_EVIDENCE_ROOT_NOT_LIST")

    f4_rows = load_jsonl(F4)

    rows = []
    f4_state_counts = Counter()
    class_counts = Counter()
    eligibility_counts = Counter()
    trade_counts = Counter()
    transitions = Counter()

    ready = 0
    unavailable = 0
    baseline_counts = Counter()

    # Baseline gate: prove that the F1-F3 states/classifications are exactly
    # the previously validated 929-record baseline before adding F4.
    for row in baseline:
        baseline_counts[str(row.get("classification") or "").upper()] += 1

    for row in baseline:
        isin = norm_isin(row.get("isin"))
        states = {
            "F1": normalize_state(row.get("f1_state")),
            "F2": normalize_state(row.get("f2_state")),
            "F3": normalize_state(row.get("f3_state")),
        }

        old_class = str(row.get("classification") or "").upper()
        f4_cache = f4_rows.get(isin, {})

        prev = f4_cache.get("previous")
        latest = f4_cache.get("latest")
        flow_raw = f4_cache.get("latest_net_flow_ratio")

        size_change = None
        flow = None
        f4_state = "UNAVAILABLE"

        if (
            f4_cache.get("reason") == "SUCCESS"
            and isinstance(prev, dict)
            and isinstance(latest, dict)
            and flow_raw not in (None, "")
        ):
            try:
                prev_nav = Decimal(str(prev.get("nav")))
                latest_nav = Decimal(str(latest.get("nav")))
                flow = Decimal(str(flow_raw))
                if prev_nav > 0 and latest_nav > 0:
                    size_change = (latest_nav / prev_nav) - Decimal("1")
                    positive = int(size_change > 0) + int(flow > 0)
                    negative = int(size_change < 0) + int(flow < 0)

                    if positive >= 2:
                        f4_state = "POSITIVE"
                    elif negative >= 2:
                        f4_state = "CAUTION"
                    else:
                        f4_state = "NEUTRAL"
            except Exception:
                size_change = None
                flow = None
                f4_state = "UNAVAILABLE"

        states["F4"] = f4_state
        new_class = classify(states, row.get("category_id"))

        class_counts[new_class] += 1
        f4_state_counts[f4_state] += 1
        transitions[(old_class, new_class)] += 1

        if f4_state in VALID_STATES:
            ready += 1
        else:
            unavailable += 1

        # Preserve baseline identity and F1-F3 fields exactly; only add F4.
        output_row = dict(row)
        output_row.update({
            "f4_state": f4_state,
            "fund_size_change": None if size_change is None else str(size_change),
            "net_flow_ratio": None if flow is None else str(flow),
            "f4_previous_date": prev.get("date") if isinstance(prev, dict) else None,
            "f4_latest_date": latest.get("date") if isinstance(latest, dict) else None,
            "classification": new_class,
            "eligibility_reason": (
                "MULTI_FAMILY_WEAKENING" if new_class == "D"
                else "BROAD_STRENGTH_WITH_RELATIVE_OR_TREND_CONFIRMATION" if new_class == "A"
                else "DEVELOPING_MULTI_FAMILY_SUPPORT" if new_class == "B"
                else "INSUFFICIENT_INDEPENDENT_EVIDENCE" if new_class == "X"
                else "OBSERVATION_REQUIRED"
            ),
            "automatic_trade_authority": "NONE",
            "forced_fill": False,
        })
        rows.append(output_row)

    OUTPUT.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "version": BRIDGE_VERSION,
        "result_count": len(rows),
        "baseline_result_count": len(baseline),
        "baseline_class_counts": dict(sorted(baseline_counts.items())),
        "f4_ready": ready,
        "f4_unavailable": unavailable,
        "f4_state_counts": dict(sorted(f4_state_counts.items())),
        "class_counts": dict(sorted(class_counts.items())),
        "eligibility_counts": dict(sorted(eligibility_counts.items())),
        "trade_authority_counts": {"NONE": len(rows)},
        "classification_transitions": {
            f"{a}->{b}": n for (a, b), n in sorted(transitions.items())
        },
        "baseline_source": "f1_f2_f3_evidence_v1_latest.json",
        "f4_source": "fh9_bamosz_turnover_progress_v11.jsonl",
        "f1_f2_f3_recomputed": False,
        "mutation": "DISCOVERY_OUTPUT_ONLY",
        "production_mutation": "NO",
        "semantic_proxy": "NO",
        "forced_fill": "NO",
    }

    SUMMARY.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("F4_BRIDGE_VERSION=" + BRIDGE_VERSION)
    print("RESULT_COUNT=" + str(len(rows)))
    print("BASELINE_RESULT_COUNT=" + str(len(baseline)))
    print("F1_F2_F3_RECOMPUTED=NO")
    print("F4_READY=" + str(ready))
    print("F4_UNAVAILABLE=" + str(unavailable))
    print("F4_STATE_COUNTS=" + json.dumps(dict(sorted(f4_state_counts.items())), sort_keys=True))
    print("BASELINE_CLASS_COUNTS=" + json.dumps(dict(sorted(baseline_counts.items())), sort_keys=True))
    print("CLASS_COUNTS=" + json.dumps(dict(sorted(class_counts.items())), sort_keys=True))
    print("CLASSIFICATION_TRANSITIONS=" + json.dumps(
        {f"{a}->{b}": n for (a, b), n in sorted(transitions.items())},
        sort_keys=True,
    ))
    print("TRADE_AUTHORITY_COUNTS=" + json.dumps({"NONE": len(rows)}, sort_keys=True))
    print("OUTPUT_JSON=" + str(OUTPUT))
    print("SUMMARY_JSON=" + str(SUMMARY))
    print("MUTATION=DISCOVERY_OUTPUT_ONLY")
    print("PRODUCTION_MUTATION=NO")
    print("SEMANTIC_PROXY=NO")
    print("FORCED_FILL=NO")
    print("STATUS_FINAL=SUCCESS")


if __name__ == "__main__":
    main()