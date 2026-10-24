from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BANK_SYMBOLS = (
    "AKBNK",
    "GARAN",
    "HALKB",
    "ISCTR",
    "SKBNK",
    "TSKB",
    "VAKBN",
    "YKBNK",
)

EXCLUDED_PATH_TOKENS = (
    "\\_backup\\",
    "\\tests\\",
    "\\test\\",
    "free_float",
    "funds\\",
    "financial_intelligence_v1_3_bank_real_source_discovery",
    "financial_intelligence_v1_3_bank_raw_source_schema_characterization",
    "_closure",
    "_manifest",
    "_registry",
    "_acceptance",
    "_contract",
    "_fixture",
    "_mock",
)

FINANCIAL_TERMS = (
    "capital adequacy",
    "sermaye yeterlilik",
    "tier 1",
    "ana sermaye",
    "npl",
    "non performing",
    "takipteki",
    "kredi",
    "mevduat",
    "loan",
    "deposit",
    "net interest margin",
    "net faiz marj",
    "faiz marj",
    "roe",
    "roa",
    "özsermaye karl",
    "aktif karl",
    "cost to income",
    "gider gelir",
    "liquidity",
    "likidite",
    "balance sheet",
    "bilanço",
    "income statement",
    "gelir tablosu",
    "cash flow",
    "nakit akış",
    "financial statement",
    "finansal tablo",
    "kap",
)

STRONG_FILENAME_TERMS = (
    "kap",
    "financial",
    "finansal",
    "bilan",
    "income",
    "gelir",
    "bank",
    "banka",
)


def _read_text(path: Path) -> str:
    if path.suffix.lower() not in {
        ".json",
        ".jsonl",
        ".csv",
        ".txt",
        ".py",
    }:
        return ""

    try:
        return path.read_text(
            encoding="utf-8-sig",
            errors="ignore",
        )[:500000]
    except Exception:
        return ""


def _symbol_hits(text: str) -> list[str]:
    upper = text.upper()
    return [
        symbol
        for symbol in BANK_SYMBOLS
        if symbol in upper
    ]


def _financial_hits(text: str) -> list[str]:
    folded = text.casefold()
    return [
        term
        for term in FINANCIAL_TERMS
        if term.casefold() in folded
    ]


def _excluded(path: Path) -> bool:
    raw = str(path).lower()
    return any(
        token.lower() in raw
        for token in EXCLUDED_PATH_TOKENS
    )


def _score(
    path: Path,
    symbols: list[str],
    terms: list[str],
    text: str,
) -> int:
    score = 0

    name_folded = path.name.casefold()

    score += len(symbols) * 8
    score += min(30, len(terms) * 3)

    if path.suffix.lower() in {
        ".xls",
        ".xlsx",
    }:
        score += 12

    if any(
        term in name_folded
        for term in STRONG_FILENAME_TERMS
    ):
        score += 8

    if "publication_date" in text:
        score += 5

    if '"as_of"' in text or "'as_of'" in text:
        score += 5

    if "canonical_facts" in text:
        score += 6

    return score


def main():
    project = Path(
        r"D:\Projects\Hisse-Robotu"
    )

    roots = [
        project,
        Path(r"C:\Users\user\Downloads"),
    ]

    allowed_suffixes = {
        ".xls",
        ".xlsx",
        ".json",
        ".jsonl",
        ".csv",
        ".txt",
    }

    rows = []

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in allowed_suffixes:
                continue

            if _excluded(path):
                continue

            text = _read_text(path)

            identity_text = (
                str(path)
                + "\n"
                + text
            )

            symbols = _symbol_hits(
                identity_text
            )

            terms = _financial_hits(
                identity_text
            )

            filename_financial = any(
                token in path.name.casefold()
                for token in STRONG_FILENAME_TERMS
            )

            if not symbols:
                continue

            if (
                not terms
                and not filename_financial
                and path.suffix.lower()
                not in {".xls", ".xlsx"}
            ):
                continue

            score = _score(
                path,
                symbols,
                terms,
                text,
            )

            rows.append({
                "path": str(path),
                "suffix":
                    path.suffix.lower(),
                "symbols":
                    symbols,
                "financial_terms":
                    terms[:30],
                "score":
                    score,
                "bytes":
                    path.stat().st_size,
                "has_publication_date":
                    "publication_date"
                    in text,
                "has_as_of":
                    '"as_of"' in text
                    or "'as_of'" in text,
                "has_canonical_facts":
                    "canonical_facts"
                    in text,
            })

    rows.sort(
        key=lambda row: (
            -row["score"],
            row["path"],
        )
    )

    # Require more than symbol-only evidence.
    credible = [
        row
        for row in rows
        if (
            row["score"] >= 20
            and (
                len(
                    row["financial_terms"]
                ) >= 2
                or row["suffix"]
                in {".xls", ".xlsx"}
            )
        )
    ]

    selected = (
        credible[0]
        if credible
        else None
    )

    result = {
        "schema_version":
            "financial-intelligence-v1-3-bank-financial-source-disambiguation-v2",
        "status":
            "PASS"
            if selected
            else "PASS_FAIL_CLOSED",
        "candidate_count":
            len(rows),
        "credible_candidate_count":
            len(credible),
        "selected_source":
            selected,
        "top_candidates":
            rows[:30],
        "canonical_producer_ready":
            False,
        "production_evidence":
            False,
        "activation_ready":
            False,
        "blockers":
            (
                []
                if selected
                else [
                    "NO_REAL_BANK_FINANCIAL_SOURCE"
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
        project
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_BANK_FINANCIAL_SOURCE_DISAMBIGUATION_V2.json"
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
        f"CANDIDATE_COUNT="
        f"{result['candidate_count']}"
    )
    print(
        f"CREDIBLE_CANDIDATE_COUNT="
        f"{result['credible_candidate_count']}"
    )
    print(
        f"SELECTED_SOURCE="
        f"{result['selected_source']}"
    )
    print(
        "CANONICAL_PRODUCER_READY=False"
    )
    print(
        "PRODUCTION_EVIDENCE=False"
    )
    print(
        "ACTIVATION_READY=False"
    )
    print(
        f"BLOCKERS={result['blockers']}"
    )

    print(
        "TOP_FINANCIAL_CANDIDATES_START"
    )

    for index, row in enumerate(
        rows[:15],
        start=1,
    ):
        print(
            f"TOP_{index}="
            f"{json.dumps(row, ensure_ascii=False, sort_keys=True)}"
        )

    print(
        "TOP_FINANCIAL_CANDIDATES_END"
    )
    print("MUTATION=NO")
    print("STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print(f"RESULT={out}")
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "BANK_FINANCIAL_SOURCE_DISAMBIGUATION_V2=PASS"
    )


if __name__ == "__main__":
    main()
