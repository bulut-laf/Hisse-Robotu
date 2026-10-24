from __future__ import annotations

import json
from pathlib import Path
from collections import Counter
from typing import Any


BANK_SYMBOLS = {
    "AKBNK",
    "GARAN",
    "HALKB",
    "ISCTR",
    "SKBNK",
    "TSKB",
    "VAKBN",
    "YKBNK",
}

CONTROL_TOKENS = (
    "_intake_gate",
    "_readiness",
    "_registry",
    "_acceptance",
    "_handoff",
    "_closure",
    "_manifest",
    "_resolution",
    "_selector",
    "_contract",
    "_test",
    "_fixture",
    "_mock",
)

FINANCIAL_HINT_KEYS = {
    "symbol",
    "ticker",
    "stockCode",
    "code",
    "sector",
    "sector_model",
    "as_of",
    "date",
    "period",
    "publication_date",
    "publishDate",
    "disclosureIndex",
    "canonical_facts",
    "facts",
    "metrics",
    "financials",
    "balance_sheet",
    "income_statement",
    "cash_flow",
}


def _iter_dicts(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _iter_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_dicts(item)


def _symbol_of(record: dict[str, Any]) -> str:
    for key in (
        "symbol",
        "ticker",
        "stockCode",
        "code",
    ):
        value = str(
            record.get(key) or ""
        ).strip().upper()

        if value.endswith(".IS"):
            value = value[:-3]

        if value in BANK_SYMBOLS:
            return value

    return ""


def _bankish(record: dict[str, Any]) -> bool:
    sector = str(
        record.get("sector_model")
        or record.get("sector")
        or ""
    ).upper()

    if "BANK" in sector or "BANKA" in sector:
        return True

    return bool(_symbol_of(record))


def _score(record: dict[str, Any]) -> int:
    keys = set(record.keys())
    score = 0

    score += 4 if _symbol_of(record) else 0
    score += 4 if str(record.get("sector_model") or "").upper() == "BANK" else 0

    for key in (
        "as_of",
        "publication_date",
        "publishDate",
        "disclosureIndex",
        "period",
    ):
        if key in record:
            score += 2

    for key in (
        "canonical_facts",
        "facts",
        "metrics",
        "financials",
        "balance_sheet",
        "income_statement",
        "cash_flow",
    ):
        if key in record:
            score += 3

    score += min(
        5,
        len(
            keys.intersection(
                FINANCIAL_HINT_KEYS
            )
        ),
    )

    return score


def main():
    root = Path(r"D:\Projects\Hisse-Robotu")

    search_roots = [
        root / "backend" / "data",
        root / "data",
    ]

    rows = []
    key_counter = Counter()
    path_counter = Counter()

    for base in search_roots:
        if not base.exists():
            continue

        for path in base.rglob("*.json"):
            lower = path.name.lower()

            if any(
                token in lower
                for token in CONTROL_TOKENS
            ):
                continue

            try:
                data = json.loads(
                    path.read_text(
                        encoding="utf-8-sig"
                    )
                )
            except Exception:
                continue

            for index, record in enumerate(
                _iter_dicts(data)
            ):
                if not _bankish(record):
                    continue

                keys = sorted(
                    str(k)
                    for k in record.keys()
                )

                for key in keys:
                    key_counter[key] += 1

                path_counter[str(path)] += 1

                row = {
                    "source_path": str(path),
                    "record_index": index,
                    "symbol":
                        _symbol_of(record)
                        or None,
                    "sector_model":
                        str(
                            record.get(
                                "sector_model"
                            )
                            or ""
                        ).strip()
                        or None,
                    "score":
                        _score(record),
                    "keys": keys[:120],
                    "date_fields": {
                        k: record.get(k)
                        for k in (
                            "as_of",
                            "publication_date",
                            "publishDate",
                            "date",
                            "period",
                        )
                        if k in record
                    },
                    "id_fields": {
                        k: record.get(k)
                        for k in (
                            "disclosureIndex",
                            "notification_id",
                            "id",
                        )
                        if k in record
                    },
                    "nested_shapes": {
                        k: (
                            "dict"
                            if isinstance(
                                record.get(k),
                                dict,
                            )
                            else "list"
                            if isinstance(
                                record.get(k),
                                list,
                            )
                            else type(
                                record.get(k)
                            ).__name__
                        )
                        for k in (
                            "canonical_facts",
                            "facts",
                            "metrics",
                            "financials",
                            "balance_sheet",
                            "income_statement",
                            "cash_flow",
                            "data",
                            "records",
                            "items",
                        )
                        if k in record
                    },
                }

                rows.append(row)

    rows.sort(
        key=lambda x: (
            -x["score"],
            x["source_path"],
            x["record_index"],
        )
    )

    top = rows[:50]

    likely_sources = [
        row
        for row in top
        if row["score"] >= 8
    ]

    result = {
        "schema_version":
            "financial-intelligence-v1-3-bank-raw-source-schema-characterization-v1",
        "status":
            "PASS"
            if rows
            else "PASS_FAIL_CLOSED",
        "bank_record_count":
            len(rows),
        "unique_source_file_count":
            len(
                {
                    row["source_path"]
                    for row in rows
                }
            ),
        "likely_source_count":
            len(likely_sources),
        "top_candidates":
            top,
        "top_keys":
            key_counter.most_common(
                80
            ),
        "source_record_counts":
            path_counter.most_common(
                50
            ),
        "canonical_producer_ready":
            False,
        "selected_raw_source":
            (
                likely_sources[0]
                if likely_sources
                else None
            ),
        "blockers":
            (
                []
                if likely_sources
                else [
                    "NO_BANK_RAW_SOURCE_SCHEMA_IDENTIFIED"
                ]
            ),
        "mutation":
            "NO",
        "store_mutation":
            "NO",
        "al_sat_mutation":
            "NO",
    }

    out = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_BANK_RAW_SOURCE_SCHEMA_CHARACTERIZATION.json"
    )

    out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out.write_text(
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
        f"BANK_RECORD_COUNT="
        f"{result['bank_record_count']}"
    )
    print(
        f"UNIQUE_SOURCE_FILE_COUNT="
        f"{result['unique_source_file_count']}"
    )
    print(
        f"LIKELY_SOURCE_COUNT="
        f"{result['likely_source_count']}"
    )
    print(
        f"SELECTED_RAW_SOURCE="
        f"{result['selected_raw_source']}"
    )
    print(
        "CANONICAL_PRODUCER_READY=False"
    )
    print(
        f"BLOCKERS={result['blockers']}"
    )

    print("TOP_CANDIDATES_START")

    for i, row in enumerate(
        top[:10],
        start=1,
    ):
        print(
            f"TOP_{i}="
            f"{json.dumps(row, ensure_ascii=False, sort_keys=True)}"
        )

    print("TOP_CANDIDATES_END")

    print("MUTATION=NO")
    print("STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print(f"RESULT={out}")
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "BANK_RAW_SOURCE_SCHEMA_CHARACTERIZATION_V1=PASS"
    )


if __name__ == "__main__":
    main()
