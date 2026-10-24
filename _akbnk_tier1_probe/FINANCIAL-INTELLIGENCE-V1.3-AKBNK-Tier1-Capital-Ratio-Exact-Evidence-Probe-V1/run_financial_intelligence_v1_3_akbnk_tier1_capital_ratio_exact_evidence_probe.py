from __future__ import annotations

import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])

text_path = (
    root
    / "backend"
    / "data"
    / "financial_intelligence"
    / "evidence"
    / "AKBNK"
    / "AKBNK_1637884_2026_2.txt"
)

result_path = (
    root
    / "backend"
    / "data"
    / "financial_intelligence"
    / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_TIER1_CAPITAL_RATIO_EXACT_EVIDENCE_PROBE.json"
)

if not text_path.exists():
    raise SystemExit(f"AKBNK_PDF_TEXT_MISSING:{text_path}")

text = text_path.read_text(encoding="utf-8-sig", errors="replace")

patterns = [
    ("ANA_SERMAYE_YETERLILIK", r"ana\s+sermaye.{0,120}?yeter"),
    ("CEKIRDEK_SERMAYE_YETERLILIK", r"çekirdek\s+sermaye.{0,120}?yeter"),
    ("TIER_1", r"\btier\s*1\b"),
    ("BIRINCIL_SERMAYE", r"birincil\s+sermaye"),
    ("SERMAYE_YETERLILIGI", r"sermaye\s+yeterlili"),
]

percent_re = re.compile(
    r"%\s*-?\d{1,3}(?:[.,]\d+)?|-?\d{1,3}(?:[.,]\d+)?\s*%",
    flags=re.IGNORECASE,
)

matches = []

for label, pattern in patterns:
    rx = re.compile(pattern, flags=re.IGNORECASE | re.DOTALL)

    for m in rx.finditer(text):
        start = max(0, m.start() - 350)
        end = min(len(text), m.end() + 700)
        context = text[start:end]
        context_clean = re.sub(r"\s+", " ", context).strip()

        percentages = percent_re.findall(context_clean)

        matches.append({
            "label": label,
            "match_text": re.sub(r"\s+", " ", m.group(0)).strip(),
            "start": m.start(),
            "percentages_in_context": percentages,
            "context": context_clean,
        })

# preserve order, cap repetitive results per label
selected = []
per_label = {}
seen_context = set()

for item in matches:
    label = item["label"]
    per_label.setdefault(label, 0)

    key = item["context"][:300]
    if key in seen_context:
        continue

    if per_label[label] >= 12:
        continue

    selected.append(item)
    seen_context.add(key)
    per_label[label] += 1

result = {
    "status": "PASS" if selected else "PASS_FAIL_CLOSED",
    "symbol": "AKBNK",
    "notification_id": "1637884",
    "target_metric": "CAPITAL_ADEQUACY.tier1_capital_ratio",
    "source_text": str(text_path),
    "candidate_context_count": len(selected),
    "candidate_contexts": selected,
    "metric_value_selected": None,
    "selection_ready": False,
    "production_evidence": True,
    "canonical_production_ready": False,
    "scoring_ready": False,
    "activation_ready": False,
    "missing_to_zero": False,
    "blockers": (
        []
        if selected
        else ["AKBNK_TIER1_EXACT_EVIDENCE_NOT_FOUND"]
    ),
    "production_mutation": "NO",
    "store_mutation": "NO",
    "al_sat_mutation": "NO",
}

result_path.write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"STATUS={result['status']}")
print(f"TARGET_METRIC={result['target_metric']}")
print(f"CANDIDATE_CONTEXT_COUNT={result['candidate_context_count']}")
print("METRIC_VALUE_SELECTED=None")
print("SELECTION_READY=False")
print("PRODUCTION_EVIDENCE=True")
print("CANONICAL_PRODUCTION_READY=False")
print("SCORING_READY=False")
print("ACTIVATION_READY=False")
print("MISSING_TO_ZERO=False")
print(f"BLOCKERS={result['blockers']}")
print("CANDIDATE_CONTEXTS_START")

for i, item in enumerate(selected, 1):
    print(f"--- CANDIDATE_{i} ---")
    print(f"LABEL={item['label']}")
    print(f"PERCENTAGES={item['percentages_in_context']}")
    print(f"CONTEXT={item['context']}")

print("CANDIDATE_CONTEXTS_END")
print(f"RESULT={result_path}")
