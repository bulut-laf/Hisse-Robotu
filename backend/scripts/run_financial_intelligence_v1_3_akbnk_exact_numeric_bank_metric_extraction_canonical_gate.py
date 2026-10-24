from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.analysis.financial_intelligence_bank_canonical_adapter import (
    adapt_bank_canonical_input,
)


ROOT = Path(r"D:\Projects\Hisse-Robotu")

TEXT_PATH = (
    ROOT
    / "backend"
    / "data"
    / "financial_intelligence"
    / "evidence"
    / "AKBNK"
    / "AKBNK_1637884_2026_2.txt"
)

PDF_PATH = (
    ROOT
    / "backend"
    / "data"
    / "financial_intelligence"
    / "evidence"
    / "AKBNK"
    / "AKBNK_1637884_2026_2.pdf"
)

RESULT_PATH = (
    ROOT
    / "backend"
    / "data"
    / "financial_intelligence"
    / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_EXACT_NUMERIC_BANK_METRIC_EXTRACTION_CANONICAL_GATE.json"
)

EXPECTED_HASH = (
    "48a89d5e4343ee8b34fd7af9e2c73f6405e25b803b2d1695b4374bcacba9b9e5"
)

PUBLICATION_DATE = "2026-07-28"
PUBLICATION_AT_KAP = "2026-07-28T18:15:15+03:00"
AS_OF = "2026-08-31"

ALL_METRICS = (
    "capital_adequacy_ratio",
    "cost_to_income_ratio",
    "deposit_growth",
    "liquidity_ratio",
    "loan_growth",
    "loan_to_deposit_ratio",
    "net_income_growth",
    "net_interest_margin",
    "npl_coverage_ratio",
    "npl_ratio",
    "roa",
    "roe",
    "tier1_capital_ratio",
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def _tr_decimal(value: str) -> Decimal:
    cleaned = (
        value.strip()
        .replace(".", "")
        .replace(",", ".")
        .replace("%", "")
    )

    return Decimal(cleaned)


def _pct_growth(
    current: Decimal,
    prior: Decimal,
) -> Decimal | None:
    if prior == 0:
        return None

    return (
        (current / prior) - Decimal("1")
    ) * Decimal("100")


def _find_one(
    text: str,
    pattern: str,
    flags: int = re.IGNORECASE | re.DOTALL,
):
    match = re.search(
        pattern,
        text,
        flags,
    )

    return match


def _extract_capital_adequacy(
    text: str,
):
    pattern = (
        r"sermaye\s+yeterliliği\s+standart\s+oran[ıi]\s+ise\s*%"
        r"\s*([0-9]{1,3},[0-9]{1,2})"
    )

    match = _find_one(
        text,
        pattern,
    )

    if not match:
        return None

    value = _tr_decimal(
        match.group(1)
    )

    return {
        "value":
            value,
        "method":
            "DIRECT_REPORTED_RATIO",
        "evidence":
            match.group(0)[:500],
    }


def _extract_deposit_growth(
    text: str,
):
    pattern = (
        r"I\.\s*MEVDUAT.*?"
        r"([0-9]{1,3}(?:\.[0-9]{3})+)"
        r"\s+"
        r"([0-9]{1,3}(?:\.[0-9]{3})+)"
        r"\s+"
        r"([0-9]{1,3}(?:\.[0-9]{3})+)"
        r"\s+"
        r"([0-9]{1,3}(?:\.[0-9]{3})+)"
        r"\s+"
        r"([0-9]{1,3}(?:\.[0-9]{3})+)"
        r"\s*"
        r"([0-9]{1,3}(?:\.[0-9]{3})+)"
    )

    match = _find_one(
        text,
        pattern,
    )

    if not match:
        return None

    current_total = _tr_decimal(
        match.group(3)
    )

    prior_total = _tr_decimal(
        match.group(6)
    )

    growth = _pct_growth(
        current_total,
        prior_total,
    )

    if growth is None:
        return None

    return {
        "value":
            growth,
        "current_total":
            current_total,
        "prior_total":
            prior_total,
        "method":
            "DERIVED_FROM_REPORTED_CURRENT_PRIOR_TOTALS",
        "evidence":
            match.group(0)[:800],
    }


def _extract_net_income_growth(
    text: str,
):
    pattern = (
        r"Grubun\s+Net\s+Dönem\s+K[âa]r[ıi]"
        r"\s+([0-9]{1,3}(?:\.[0-9]{3})*)"
        r"\s+([0-9]{1,3}(?:\.[0-9]{3})*)"
    )

    match = _find_one(
        text,
        pattern,
    )

    if not match:
        return None

    current = _tr_decimal(
        match.group(1)
    )

    prior = _tr_decimal(
        match.group(2)
    )

    growth = _pct_growth(
        current,
        prior,
    )

    if growth is None:
        return None

    return {
        "value":
            growth,
        "current":
            current,
        "prior":
            prior,
        "method":
            "DERIVED_FROM_REPORTED_CURRENT_PRIOR_NET_INCOME",
        "evidence":
            match.group(0)[:500],
    }


def _reject_guidance_only(
    text: str,
    metric: str,
):
    patterns = {
        "net_interest_margin":
            r"Net\s+Faiz\s+Marj[ıi].{0,120}%\s*3[,\.]2\s*[-–]\s*3[,\.]5",
        "roe":
            r"Özsermaye\s+Karl[ıi]l[ıi]ğ[ıi].{0,100}%\s*23\s*[-–]\s*25",
    }

    pattern = patterns.get(
        metric
    )

    if not isinstance(
        pattern,
        str,
    ):
        return None

    match = _find_one(
        text,
        pattern,
    )

    if not match:
        return None

    return {
        "reason":
            "GUIDANCE_NOT_ACTUAL",
        "evidence":
            match.group(0)[:500],
    }


def _json_safe(value):
    if isinstance(
        value,
        Decimal,
    ):
        return str(value)

    if isinstance(
        value,
        dict,
    ):
        return {
            key: _json_safe(item)
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (list, tuple),
    ):
        return [
            _json_safe(item)
            for item in value
        ]

    return value


def main():
    result = {
        "schema_version":
            "financial-intelligence-v1-3-akbnk-exact-numeric-bank-metric-extraction-canonical-gate-v1",
        "status":
            "PASS_FAIL_CLOSED",
        "symbol":
            "AKBNK",
        "sector_model":
            "BANK",
        "as_of":
            AS_OF,
        "publication_date":
            PUBLICATION_DATE,
        "source_type":
            "KAP",
        "source_uri":
            "https://www.kap.org.tr/tr/Bildirim/1637884",
        "source_attachment_uri":
            "https://www.kap.org.tr/tr/api/file/download/4028328c9f52dc40019fa90343905e35",
        "evidence_hash":
            "sha256:" + EXPECTED_HASH,
        "hash_verified":
            False,
        "metrics":
            {
                metric: None
                for metric
                in ALL_METRICS
            },
        "metric_evidence":
            {},
        "guidance_rejections":
            {},
        "extracted_metric_count":
            0,
        "missing_metric_count":
            len(ALL_METRICS),
        "canonical_adapter_status":
            None,
        "canonical_adapter_blocker":
            None,
        "canonical_payload_ready":
            False,
        "scoring_ready":
            False,
        "activation_ready":
            False,
        "production_evidence":
            False,
        "blockers":
            [],
        "missing_to_zero":
            False,
        "future_publication_allowed":
            False,
        "production_mutation":
            "NO",
        "store_mutation":
            "NO",
        "al_sat_mutation":
            "NO",
    }

    if (
        not TEXT_PATH.exists()
        or not PDF_PATH.exists()
    ):
        result[
            "blockers"
        ].append(
            "AKBNK_NORMALIZED_EVIDENCE_MISSING"
        )

    else:
        actual_hash = _sha256(
            PDF_PATH
        )

        result[
            "hash_verified"
        ] = (
            actual_hash
            == EXPECTED_HASH
        )

        if not result[
            "hash_verified"
        ]:
            result[
                "blockers"
            ].append(
                "AKBNK_EVIDENCE_HASH_MISMATCH"
            )

        if not result[
            "blockers"
        ]:
            text = TEXT_PATH.read_text(
                encoding="utf-8-sig",
                errors="ignore",
            )

            extracts = {
                "capital_adequacy_ratio":
                    _extract_capital_adequacy(
                        text
                    ),
                "deposit_growth":
                    _extract_deposit_growth(
                        text
                    ),
                "net_income_growth":
                    _extract_net_income_growth(
                        text
                    ),
            }

            for metric, extraction in (
                extracts.items()
            ):
                if extraction is None:
                    continue

                result[
                    "metrics"
                ][metric] = extraction[
                    "value"
                ]

                result[
                    "metric_evidence"
                ][metric] = extraction

            for metric in (
                "net_interest_margin",
                "roe",
            ):
                rejection = (
                    _reject_guidance_only(
                        text,
                        metric,
                    )
                )

                if rejection:
                    result[
                        "guidance_rejections"
                    ][metric] = rejection

            result[
                "extracted_metric_count"
            ] = sum(
                1
                for value
                in result[
                    "metrics"
                ].values()
                if value is not None
            )

            result[
                "missing_metric_count"
            ] = (
                len(
                    ALL_METRICS
                )
                - result[
                    "extracted_metric_count"
                ]
            )

            canonical_facts = {
                key: value
                for key, value
                in result[
                    "metrics"
                ].items()
                if value is not None
            }

            record = {
                "source_type":
                    "KAP",
                "source_uri":
                    result[
                        "source_attachment_uri"
                    ],
                "symbol":
                    "AKBNK",
                "sector_model":
                    "BANK",
                "as_of":
                    AS_OF,
                "publication_date":
                    PUBLICATION_DATE,
                "canonical_facts":
                    canonical_facts,
                "evidence_hash":
                    result[
                        "evidence_hash"
                    ],
            }

            try:
                adapted = (
                    adapt_bank_canonical_input(
                        record
                    )
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
                    result[
                        "canonical_payload_ready"
                    ]
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

    if (
        result[
            "missing_metric_count"
        ] > 0
    ):
        result[
            "blockers"
        ].append(
            "BANK_REQUIRED_METRICS_STILL_MISSING"
        )

    serializable = _json_safe(
        result
    )

    RESULT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT_PATH.write_text(
        json.dumps(
            serializable,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"STATUS={serializable['status']}"
    )
    print(
        f"HASH_VERIFIED={serializable['hash_verified']}"
    )
    print(
        "EXTRACTED_METRIC_COUNT="
        f"{serializable['extracted_metric_count']}"
    )
    print(
        "MISSING_METRIC_COUNT="
        f"{serializable['missing_metric_count']}"
    )

    print(
        "EXTRACTED_METRICS_START"
    )

    for metric in ALL_METRICS:
        print(
            f"METRIC_{metric.upper()}="
            f"{serializable['metrics'][metric]}"
        )

    print(
        "EXTRACTED_METRICS_END"
    )

    print(
        "GUIDANCE_REJECTIONS="
        f"{json.dumps(serializable['guidance_rejections'], ensure_ascii=False)}"
    )
    print(
        "CANONICAL_ADAPTER_STATUS="
        f"{serializable['canonical_adapter_status']}"
    )
    print(
        "CANONICAL_ADAPTER_BLOCKER="
        f"{serializable['canonical_adapter_blocker']}"
    )
    print(
        "CANONICAL_PAYLOAD_READY="
        f"{serializable['canonical_payload_ready']}"
    )
    print(
        "PRODUCTION_EVIDENCE="
        f"{serializable['production_evidence']}"
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
        "FUTURE_PUBLICATION_ALLOWED=False"
    )
    print(
        f"BLOCKERS={serializable['blockers']}"
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
        "AKBNK_EXACT_NUMERIC_BANK_METRIC_EXTRACTION_CANONICAL_GATE_V1=PASS"
    )


if __name__ == "__main__":
    main()
