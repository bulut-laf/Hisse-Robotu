from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


BANK_TOKENS = (
    "BANK",
    "BANKA",
    "BANKACILIK",
)

SYMBOL_HINTS = (
    "AKBNK",
    "GARAN",
    "HALKB",
    "ISCTR",
    "SKBNK",
    "TSKB",
    "VAKBN",
    "YKBNK",
)

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


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


def _iter_dicts(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _iter_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_dicts(item)


def _looks_bankish(path: Path, text: str) -> bool:
    upper = (
        path.name.upper()
        + "\n"
        + text.upper()
    )

    return any(
        token in upper
        for token in BANK_TOKENS + SYMBOL_HINTS
    )


def main():
    root = Path(r"D:\Projects\Hisse-Robotu")

    search_roots = [
        root / "backend" / "data",
        root / "data",
    ]

    candidates = []
    canonical_candidates = []
    evidence_files = []

    for base in search_roots:
        if not base.exists():
            continue

        for path in base.rglob("*"):
            if not path.is_file():
                continue

            lower_name = path.name.lower()

            if any(
                token in lower_name
                for token in CONTROL_TOKENS
            ):
                continue

            if path.suffix.lower() not in {
                ".json",
                ".jsonl",
                ".csv",
                ".txt",
                ".xls",
                ".xlsx",
                ".pdf",
            }:
                continue

            try:
                if path.suffix.lower() == ".json":
                    raw_text = path.read_text(
                        encoding="utf-8-sig"
                    )
                elif path.suffix.lower() in {
                    ".jsonl",
                    ".csv",
                    ".txt",
                }:
                    raw_text = path.read_text(
                        encoding="utf-8-sig",
                        errors="ignore",
                    )
                else:
                    raw_text = path.name
            except Exception:
                raw_text = path.name

            if not _looks_bankish(
                path,
                raw_text[:200000],
            ):
                continue

            item = {
                "path": str(path),
                "suffix": path.suffix.lower(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }

            evidence_files.append(item)

            if path.suffix.lower() == ".json":
                try:
                    data = _load_json(path)
                except Exception:
                    continue

                for record in _iter_dicts(data):
                    sector = str(
                        record.get(
                            "sector_model"
                        )
                        or ""
                    ).strip().upper()

                    symbol = str(
                        record.get(
                            "symbol"
                        )
                        or record.get(
                            "stockCode"
                        )
                        or record.get(
                            "ticker"
                        )
                        or ""
                    ).strip().upper()

                    if (
                        sector == "BANK"
                        or symbol in SYMBOL_HINTS
                    ):
                        row = {
                            "source_path": str(path),
                            "symbol": symbol or None,
                            "sector_model":
                                sector or None,
                            "has_as_of":
                                bool(
                                    str(
                                        record.get(
                                            "as_of"
                                        )
                                        or ""
                                    ).strip()
                                ),
                            "has_publication_date":
                                bool(
                                    str(
                                        record.get(
                                            "publication_date"
                                        )
                                        or ""
                                    ).strip()
                                ),
                            "has_canonical_facts":
                                isinstance(
                                    record.get(
                                        "canonical_facts"
                                    ),
                                    dict,
                                ),
                            "record_keys":
                                sorted(
                                    str(k)
                                    for k
                                    in record.keys()
                                )[:80],
                        }

                        candidates.append(
                            row
                        )

                        if (
                            row[
                                "has_as_of"
                            ]
                            and row[
                                "has_publication_date"
                            ]
                            and row[
                                "has_canonical_facts"
                            ]
                        ):
                            canonical_candidates.append(
                                row
                            )

    out = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_BANK_REAL_SOURCE_DISCOVERY.json"
    )

    out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = {
        "schema_version":
            "financial-intelligence-v1-3-bank-real-source-discovery-v1",
        "status":
            "PASS"
            if canonical_candidates
            else "PASS_FAIL_CLOSED",
        "evidence_file_count":
            len(evidence_files),
        "bank_record_candidate_count":
            len(candidates),
        "canonical_candidate_count":
            len(canonical_candidates),
        "canonical_candidates":
            canonical_candidates[:50],
        "bank_record_candidates":
            candidates[:100],
        "evidence_files":
            evidence_files[:100],
        "selected_source":
            (
                canonical_candidates[0]
                if canonical_candidates
                else None
            ),
        "production_evidence":
            bool(
                canonical_candidates
            ),
        "activation_ready":
            False,
        "blockers":
            (
                []
                if canonical_candidates
                else [
                    "NO_REAL_BANK_CANONICAL_SOURCE_DISCOVERED"
                ]
            ),
        "mutation":
            "NO",
        "store_mutation":
            "NO",
        "al_sat_mutation":
            "NO",
    }

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
        f"EVIDENCE_FILE_COUNT="
        f"{result['evidence_file_count']}"
    )
    print(
        f"BANK_RECORD_CANDIDATE_COUNT="
        f"{result['bank_record_candidate_count']}"
    )
    print(
        f"CANONICAL_CANDIDATE_COUNT="
        f"{result['canonical_candidate_count']}"
    )
    print(
        f"SELECTED_SOURCE="
        f"{result['selected_source']}"
    )
    print(
        f"PRODUCTION_EVIDENCE="
        f"{result['production_evidence']}"
    )
    print(
        "ACTIVATION_READY=False"
    )
    print(
        f"BLOCKERS={result['blockers']}"
    )
    print("MUTATION=NO")
    print("STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print(f"RESULT={out}")
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "BANK_REAL_SOURCE_DISCOVERY_EVIDENCE_INTAKE_V1=PASS"
    )


if __name__ == "__main__":
    main()
