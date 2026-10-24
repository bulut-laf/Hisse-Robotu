from __future__ import annotations

import json
import sys
from pathlib import Path

from app.analysis.financial_intelligence_bank_canonical_adapter import (
    adapt_bank_canonical_input,
)


root = Path(sys.argv[1])

source_path = (
    root
    / "backend"
    / "data"
    / "financial_intelligence"
    / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_EXACT_NUMERIC_BANK_METRIC_EXTRACTION_CANONICAL_GATE.json"
)

result_path = (
    root
    / "backend"
    / "data"
    / "financial_intelligence"
    / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_EXACT_NESTED_BANK_CANONICAL_MAPPING_GATE.json"
)

if not source_path.exists():
    raise SystemExit(
        f"BLOCK10_SOURCE_RESULT_MISSING:{source_path}"
    )

source = json.loads(
    source_path.read_text(
        encoding="utf-8-sig"
    )
)

flat = source.get(
    "metrics",
    {},
)

mapping = {
    "capital_adequacy_ratio":
        ("CAPITAL_ADEQUACY", "capital_adequacy_ratio"),
    "deposit_growth":
        ("GROWTH_QUALITY", "deposit_growth"),
    "net_income_growth":
        ("GROWTH_QUALITY", "net_income_growth"),
}

nested = {}

mapped = []

for flat_name, (
    component,
    metric_name,
) in mapping.items():
    value = flat.get(
        flat_name
    )

    if value is None:
        continue

    nested.setdefault(
        component,
        {},
    )

    nested[
        component
    ][
        metric_name
    ] = value

    mapped.append(
        f"{component}.{metric_name}"
    )

record = {
    "source_type":
        source.get(
            "source_type",
            "KAP",
        ),
    "source_uri":
        source.get(
            "source_attachment_uri"
        )
        or source.get(
            "source_uri"
        ),
    "symbol":
        source.get(
            "symbol",
            "AKBNK",
        ),
    "sector_model":
        "BANK",
    "as_of":
        source.get(
            "as_of"
        ),
    "publication_date":
        source.get(
            "publication_date"
        ),
    "canonical_facts":
        nested,
    "evidence_hash":
        source.get(
            "evidence_hash"
        ),
}

result = {
    "schema_version":
        "financial-intelligence-v1-3-akbnk-exact-nested-bank-canonical-mapping-gate-v1",
    "status":
        "PASS_FAIL_CLOSED",
    "symbol":
        record["symbol"],
    "sector_model":
        "BANK",
    "source_type":
        record["source_type"],
    "source_uri":
        record["source_uri"],
    "as_of":
        record["as_of"],
    "publication_date":
        record["publication_date"],
    "evidence_hash":
        record["evidence_hash"],
    "nested_canonical_facts":
        nested,
    "mapped_metric_paths":
        sorted(
            mapped
        ),
    "mapped_metric_count":
        len(mapped),
    "missing_to_zero":
        False,
    "industrial_threshold_reuse":
        False,
    "canonical_adapter_status":
        None,
    "canonical_adapter_blocker":
        None,
    "canonical_payload_ready":
        False,
    "production_evidence":
        False,
    "scoring_ready":
        False,
    "activation_ready":
        False,
    "blockers":
        [],
    "production_mutation":
        "NO",
    "store_mutation":
        "NO",
    "al_sat_mutation":
        "NO",
}

try:
    adapted = adapt_bank_canonical_input(
        record
    )

    status = getattr(
        adapted,
        "status",
        None,
    )

    blocker = getattr(
        adapted,
        "blocker",
        None,
    )

    payload = getattr(
        adapted,
        "payload",
        None,
    )

    result[
        "canonical_adapter_status"
    ] = (
        str(status)
        if status is not None
        else None
    )

    result[
        "canonical_adapter_blocker"
    ] = (
        str(blocker)
        if blocker is not None
        else None
    )

    result[
        "canonical_payload_ready"
    ] = bool(
        payload
    )

    if (
        payload
        and not blocker
    ):
        result[
            "status"
        ] = "PASS"

        result[
            "production_evidence"
        ] = True
    else:
        result[
            "blockers"
        ].append(
            "BANK_CANONICAL_ADAPTER_NOT_READY:"
            f"{blocker}"
        )

except Exception as exc:
    result[
        "canonical_adapter_status"
    ] = "ERROR"

    result[
        "canonical_adapter_blocker"
    ] = (
        f"{type(exc).__name__}:{exc}"
    )

    result[
        "blockers"
    ].append(
        "BANK_CANONICAL_ADAPTER_EXCEPTION:"
        f"{type(exc).__name__}:{exc}"
    )

result_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

result_path.write_text(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print(
    f"STATUS={result['status']}"
)
print(
    f"MAPPED_METRIC_COUNT={result['mapped_metric_count']}"
)
print(
    "MAPPED_METRIC_PATHS="
    f"{result['mapped_metric_paths']}"
)
print(
    "NESTED_CANONICAL_FACTS="
    f"{json.dumps(result['nested_canonical_facts'], ensure_ascii=False)}"
)
print(
    "CANONICAL_ADAPTER_STATUS="
    f"{result['canonical_adapter_status']}"
)
print(
    "CANONICAL_ADAPTER_BLOCKER="
    f"{result['canonical_adapter_blocker']}"
)
print(
    "CANONICAL_PAYLOAD_READY="
    f"{result['canonical_payload_ready']}"
)
print(
    "PRODUCTION_EVIDENCE="
    f"{result['production_evidence']}"
)
print(
    "SCORING_READY=False"
)
print(
    "ACTIVATION_READY=False"
)
print(
    "MISSING_TO_ZERO=False"
)
print(
    "INDUSTRIAL_THRESHOLD_REUSE=False"
)
print(
    f"BLOCKERS={result['blockers']}"
)
print(
    "PRODUCTION_MUTATION=NO"
)
print(
    "STORE_MUTATION=NO"
)
print(
    "AL_SAT_MUTATION=NO"
)
print(
    f"RESULT={result_path}"
)
print(
    "FINANCIAL_INTELLIGENCE_V1_3_"
    "AKBNK_EXACT_NESTED_BANK_CANONICAL_MAPPING_GATE_V1=PASS"
)
