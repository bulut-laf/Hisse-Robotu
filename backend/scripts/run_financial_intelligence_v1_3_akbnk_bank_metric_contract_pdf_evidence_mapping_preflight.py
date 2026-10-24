from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(r"D:\Projects\Hisse-Robotu")

MODEL_FILES = (
    ROOT
    / "backend"
    / "app"
    / "analysis"
    / "financial_intelligence_bank_model_contract.py",
    ROOT
    / "backend"
    / "app"
    / "analysis"
    / "financial_intelligence_bank_scoring_engine.py",
    ROOT
    / "backend"
    / "app"
    / "analysis"
    / "financial_intelligence_bank_canonical_adapter.py",
)

TEXT_PATH = (
    ROOT
    / "backend"
    / "data"
    / "financial_intelligence"
    / "evidence"
    / "AKBNK"
    / "AKBNK_1637884_2026_2.txt"
)

RESULT_PATH = (
    ROOT
    / "backend"
    / "data"
    / "financial_intelligence"
    / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_BANK_METRIC_CONTRACT_PDF_EVIDENCE_MAPPING_PREFLIGHT.json"
)


GENERIC_EXCLUDE = {
    "pass",
    "fail",
    "bank",
    "industrial",
    "score",
    "status",
    "metric",
    "metrics",
    "component",
    "components",
    "weight",
    "weights",
    "strong",
    "healthy",
    "watch",
    "weak",
    "high",
    "low",
    "medium",
    "missing",
    "invalid",
    "none",
    "ready",
    "locked",
    "unknown",
    "percentage",
    "ratio",
    "value",
    "unit",
    "reason",
    "reasons",
    "warning",
    "warnings",
}


SYNONYMS = {
    "capital_adequacy_ratio": (
        "sermaye yeterlilik",
        "sermaye yeterliliği",
        "capital adequacy",
    ),
    "tier1_ratio": (
        "ana sermaye yeterlilik",
        "ana sermaye oran",
        "çekirdek sermaye yeterlilik",
        "tier 1",
        "core tier",
    ),
    "npl_ratio": (
        "takipteki krediler",
        "takipteki alacaklar",
        "takipteki kredi oran",
        "non-performing",
        "npl",
    ),
    "loan_to_deposit_ratio": (
        "kredi mevduat oran",
        "kredilerin mevduata oranı",
        "loan to deposit",
    ),
    "net_interest_margin": (
        "net faiz marj",
        "net interest margin",
    ),
    "cost_to_income_ratio": (
        "gider gelir oran",
        "faaliyet giderleri gelir",
        "cost to income",
    ),
    "roe": (
        "özkaynak kârlılık",
        "özkaynak karlılık",
        "return on equity",
        "roe",
    ),
    "roa": (
        "aktif kârlılık",
        "aktif karlılık",
        "return on assets",
        "roa",
    ),
    "liquidity_ratio": (
        "likidite oran",
        "liquidity ratio",
    ),
    "deposit_growth": (
        "mevduat",
        "deposit",
    ),
    "loan_growth": (
        "krediler",
        "loan",
    ),
    "net_income_growth": (
        "net dönem kâr",
        "net dönem kar",
        "net profit",
    ),
}


def _snake_like(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"[a-z][a-z0-9_]{2,64}",
            value,
        )
    )


def _string_literals(path: Path) -> set[str]:
    text = path.read_text(
        encoding="utf-8-sig",
        errors="ignore",
    )

    tree = ast.parse(text)
    found: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(
            node,
            ast.Constant,
        ) and isinstance(
            node.value,
            str,
        ):
            value = node.value.strip()

            if _snake_like(value):
                found.add(value)

    return found


def _dict_keys(path: Path) -> set[str]:
    text = path.read_text(
        encoding="utf-8-sig",
        errors="ignore",
    )

    tree = ast.parse(text)
    found: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue

        for key in node.keys:
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
            ):
                value = key.value.strip()

                if _snake_like(value):
                    found.add(value)

    return found


def _metric_candidates() -> list[str]:
    values: set[str] = set()

    for path in MODEL_FILES:
        if not path.exists():
            continue

        values |= _string_literals(path)
        values |= _dict_keys(path)

    result = []

    for value in sorted(values):
        if value in GENERIC_EXCLUDE:
            continue

        if value.startswith(
            (
                "bank_",
                "financial_",
                "canonical_",
                "production_",
                "source_",
                "model_",
                "sector_",
                "status_",
                "blocker_",
            )
        ):
            continue

        if any(
            token in value
            for token in (
                "ratio",
                "margin",
                "growth",
                "coverage",
                "roe",
                "roa",
                "deposit",
                "loan",
                "npl",
                "capital",
                "liquidity",
                "income",
                "profit",
                "equity",
                "asset",
            )
        ):
            result.append(value)

    return result


def _normalize(value: str) -> str:
    value = value.casefold()
    value = value.replace("ı", "i")
    value = value.replace("ş", "s")
    value = value.replace("ğ", "g")
    value = value.replace("ü", "u")
    value = value.replace("ö", "o")
    value = value.replace("ç", "c")
    value = re.sub(
        r"\s+",
        " ",
        value,
    )
    return value.strip()


def _variants(metric: str) -> tuple[str, ...]:
    explicit = SYNONYMS.get(
        metric,
        (),
    )

    generated = (
        metric,
        metric.replace("_", " "),
    )

    seen = []
    for item in (
        *explicit,
        *generated,
    ):
        if item not in seen:
            seen.append(item)

    return tuple(seen)


def _contexts(
    text: str,
    variants: tuple[str, ...],
    *,
    max_contexts: int = 8,
):
    lines = text.splitlines()
    rows = []

    normalized_variants = [
        _normalize(v)
        for v in variants
    ]

    for i, line in enumerate(lines):
        normalized_line = _normalize(
            line
        )

        if not any(
            variant
            and variant
            in normalized_line
            for variant
            in normalized_variants
        ):
            continue

        start = max(
            0,
            i - 2,
        )

        end = min(
            len(lines),
            i + 3,
        )

        context = " | ".join(
            row.strip()
            for row
            in lines[start:end]
            if row.strip()
        )

        if context:
            rows.append({
                "line_index":
                    i + 1,
                "context":
                    context[:1800],
            })

        if len(rows) >= max_contexts:
            break

    return rows


def main():
    missing_model_files = [
        str(path)
        for path in MODEL_FILES
        if not path.exists()
    ]

    result = {
        "schema_version":
            "financial-intelligence-v1-3-akbnk-bank-metric-contract-pdf-evidence-mapping-preflight-v1",
        "status":
            "PASS_FAIL_CLOSED",
        "model_files":
            [
                str(path)
                for path in MODEL_FILES
            ],
        "missing_model_files":
            missing_model_files,
        "text_path":
            str(TEXT_PATH),
        "contract_metric_candidates":
            [],
        "metric_evidence":
            {},
        "metric_candidate_count":
            0,
        "metric_with_evidence_count":
            0,
        "metric_without_evidence_count":
            0,
        "mapping_preflight_ready":
            False,
        "numeric_mapping_ready":
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

    if missing_model_files:
        result[
            "blockers"
        ].append(
            "BANK_MODEL_CONTRACT_FILES_MISSING"
        )

    if not TEXT_PATH.exists():
        result[
            "blockers"
        ].append(
            "AKBNK_EXTRACTED_FINANCIAL_TEXT_MISSING"
        )

    if not result["blockers"]:
        text = TEXT_PATH.read_text(
            encoding="utf-8-sig",
            errors="ignore",
        )

        metrics = _metric_candidates()

        result[
            "contract_metric_candidates"
        ] = metrics
        result[
            "metric_candidate_count"
        ] = len(metrics)

        evidence = {}

        for metric in metrics:
            variants = _variants(
                metric
            )

            contexts = _contexts(
                text,
                variants,
            )

            evidence[metric] = {
                "variants":
                    list(variants),
                "evidence_present":
                    bool(contexts),
                "contexts":
                    contexts,
            }

        result[
            "metric_evidence"
        ] = evidence

        with_evidence = sum(
            1
            for row
            in evidence.values()
            if row[
                "evidence_present"
            ]
        )

        result[
            "metric_with_evidence_count"
        ] = with_evidence

        result[
            "metric_without_evidence_count"
        ] = (
            len(metrics)
            - with_evidence
        )

        if metrics and with_evidence:
            result[
                "status"
            ] = "PASS"

            result[
                "mapping_preflight_ready"
            ] = True

        else:
            result[
                "blockers"
            ].append(
                "BANK_METRIC_CONTRACT_EVIDENCE_NOT_FOUND"
            )

    RESULT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT_PATH.write_text(
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
        "MODEL_FILE_COUNT="
        f"{len(result['model_files'])}"
    )
    print(
        "MISSING_MODEL_FILE_COUNT="
        f"{len(result['missing_model_files'])}"
    )
    print(
        "METRIC_CANDIDATE_COUNT="
        f"{result['metric_candidate_count']}"
    )
    print(
        "METRIC_WITH_EVIDENCE_COUNT="
        f"{result['metric_with_evidence_count']}"
    )
    print(
        "METRIC_WITHOUT_EVIDENCE_COUNT="
        f"{result['metric_without_evidence_count']}"
    )
    print(
        "MAPPING_PREFLIGHT_READY="
        f"{result['mapping_preflight_ready']}"
    )

    print(
        "CONTRACT_METRICS_START"
    )

    for index, metric in enumerate(
        result[
            "contract_metric_candidates"
        ],
        start=1,
    ):
        row = result[
            "metric_evidence"
        ][metric]

        print(
            f"METRIC_{index}="
            f"{metric}"
            f"|EVIDENCE={row['evidence_present']}"
            f"|CONTEXT_COUNT={len(row['contexts'])}"
        )

        for context_index, context in enumerate(
            row["contexts"][:2],
            start=1,
        ):
            print(
                f"METRIC_{index}_CTX_{context_index}="
                f"{json.dumps(context, ensure_ascii=False, sort_keys=True)}"
            )

    print(
        "CONTRACT_METRICS_END"
    )

    print(
        "NUMERIC_MAPPING_READY=False"
    )
    print(
        "SCORING_READY=False"
    )
    print(
        "ACTIVATION_READY=False"
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
        f"RESULT={RESULT_PATH}"
    )
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "AKBNK_BANK_METRIC_CONTRACT_PDF_EVIDENCE_MAPPING_PREFLIGHT_V1=PASS"
    )


if __name__ == "__main__":
    main()
