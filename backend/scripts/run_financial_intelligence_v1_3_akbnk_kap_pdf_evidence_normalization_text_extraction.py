from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path


EXPECTED_SHA256 = (
    "48a89d5e4343ee8b34fd7af9e2c73f6405e25b803b2d1695b4374bcacba9b9e5"
)

SOURCE_MISNAMED = (
    Path(r"D:\Projects\Hisse-Robotu")
    / "backend"
    / "data"
    / "financial_intelligence"
    / "evidence"
    / "AKBNK"
    / "AKBNK_1637884_2026_2.xls"
)

NORMALIZED_PDF = (
    Path(r"D:\Projects\Hisse-Robotu")
    / "backend"
    / "data"
    / "financial_intelligence"
    / "evidence"
    / "AKBNK"
    / "AKBNK_1637884_2026_2.pdf"
)

TEXT_OUTPUT = (
    Path(r"D:\Projects\Hisse-Robotu")
    / "backend"
    / "data"
    / "financial_intelligence"
    / "evidence"
    / "AKBNK"
    / "AKBNK_1637884_2026_2.txt"
)

RESULT_PATH = (
    Path(r"D:\Projects\Hisse-Robotu")
    / "backend"
    / "data"
    / "financial_intelligence"
    / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_KAP_PDF_EVIDENCE_NORMALIZATION_TEXT_EXTRACTION.json"
)

TERMS = {
    "capital_adequacy": (
        "sermaye yeterlilik",
        "capital adequacy",
    ),
    "tier_1": (
        "ana sermaye",
        "çekirdek sermaye",
        "tier 1",
        "core tier",
    ),
    "loans": (
        "krediler",
        "loans",
    ),
    "deposits": (
        "mevduat",
        "deposits",
    ),
    "npl": (
        "takipteki krediler",
        "takipteki alacaklar",
        "non-performing",
        "npl",
    ),
    "net_income": (
        "net dönem kârı",
        "net dönem karı",
        "dönem net kârı",
        "dönem net karı",
        "net profit",
    ),
    "equity": (
        "özkaynak",
        "öz kaynak",
        "equity",
    ),
    "total_assets": (
        "toplam aktif",
        "toplam varlık",
        "total assets",
    ),
    "interest_income": (
        "faiz gelirleri",
        "interest income",
    ),
    "interest_expense": (
        "faiz giderleri",
        "interest expense",
    ),
    "roa": (
        "aktif kârlılık",
        "aktif karlılık",
        "return on assets",
        "roa",
    ),
    "roe": (
        "özkaynak kârlılık",
        "özkaynak karlılık",
        "return on equity",
        "roe",
    ),
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def _extract_with_pymupdf(path: Path):
    import fitz

    document = fitz.open(path)

    pages = []

    for index, page in enumerate(
        document,
        start=1,
    ):
        text = page.get_text("text") or ""

        pages.append(
            f"\n===== PAGE {index} =====\n{text}"
        )

    return (
        "\n".join(pages),
        len(document),
        "PYMUPDF",
    )


def _extract_with_pypdf(path: Path):
    from pypdf import PdfReader

    reader = PdfReader(
        str(path)
    )

    pages = []

    for index, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text() or ""

        pages.append(
            f"\n===== PAGE {index} =====\n{text}"
        )

    return (
        "\n".join(pages),
        len(reader.pages),
        "PYPDF",
    )


def _extract_with_pypdf2(path: Path):
    from PyPDF2 import PdfReader

    reader = PdfReader(
        str(path)
    )

    pages = []

    for index, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text() or ""

        pages.append(
            f"\n===== PAGE {index} =====\n{text}"
        )

    return (
        "\n".join(pages),
        len(reader.pages),
        "PYPDF2",
    )


def _extract_text(path: Path):
    errors = []

    for extractor in (
        _extract_with_pymupdf,
        _extract_with_pypdf,
        _extract_with_pypdf2,
    ):
        try:
            text, pages, engine = extractor(
                path
            )

            if text.strip():
                return (
                    text,
                    pages,
                    engine,
                    errors,
                )

            errors.append(
                f"{extractor.__name__}:EMPTY_TEXT"
            )

        except Exception as exc:
            errors.append(
                f"{extractor.__name__}:"
                f"{type(exc).__name__}:{exc}"
            )

    return (
        "",
        0,
        None,
        errors,
    )


def _normalize_text(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.casefold(),
    ).strip()


def _term_evidence(text: str):
    normalized = _normalize_text(
        text
    )

    evidence = {}

    for metric, variants in TERMS.items():
        hits = []

        for variant in variants:
            folded = _normalize_text(
                variant
            )

            count = normalized.count(
                folded
            )

            if count:
                hits.append({
                    "term":
                        variant,
                    "count":
                        count,
                })

        evidence[metric] = {
            "present":
                bool(hits),
            "hits":
                hits,
        }

    return evidence


def _snippet_rows(
    text: str,
    *,
    max_rows: int = 80,
):
    rows = []

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    all_terms = tuple(
        term.casefold()
        for variants
        in TERMS.values()
        for term in variants
    )

    for index, line in enumerate(
        lines
    ):
        folded = line.casefold()

        if not any(
            term in folded
            for term in all_terms
        ):
            continue

        start = max(
            0,
            index - 1,
        )

        end = min(
            len(lines),
            index + 2,
        )

        rows.append(
            " | ".join(
                lines[start:end]
            )[:1200]
        )

        if len(rows) >= max_rows:
            break

    return rows


def main():
    result = {
        "schema_version":
            "financial-intelligence-v1-3-akbnk-kap-pdf-evidence-normalization-text-extraction-v1",
        "status":
            "PASS_FAIL_CLOSED",
        "source_path":
            str(SOURCE_MISNAMED),
        "normalized_pdf_path":
            str(NORMALIZED_PDF),
        "text_output_path":
            str(TEXT_OUTPUT),
        "expected_sha256":
            EXPECTED_SHA256,
        "actual_sha256":
            None,
        "pdf_magic":
            False,
        "hash_match":
            False,
        "normalized_copy_written":
            False,
        "extraction_engine":
            None,
        "page_count":
            0,
        "text_char_count":
            0,
        "term_evidence":
            {},
        "metric_family_present_count":
            0,
        "financial_text_ready":
            False,
        "bank_metric_mapping_ready":
            False,
        "scoring_ready":
            False,
        "activation_ready":
            False,
        "extraction_errors":
            [],
        "evidence_snippets":
            [],
        "blockers":
            [],
        "source_bytes_mutated":
            "NO",
        "store_mutation":
            "NO",
        "al_sat_mutation":
            "NO",
    }

    if not SOURCE_MISNAMED.exists():
        result[
            "blockers"
        ].append(
            "AKBNK_ATTACHMENT_SOURCE_MISSING"
        )

    else:
        actual_hash = _sha256(
            SOURCE_MISNAMED
        )

        result[
            "actual_sha256"
        ] = actual_hash

        result[
            "hash_match"
        ] = (
            actual_hash
            == EXPECTED_SHA256
        )

        with SOURCE_MISNAMED.open(
            "rb"
        ) as f:
            magic = f.read(5)

        result[
            "pdf_magic"
        ] = (
            magic == b"%PDF-"
        )

        if not result[
            "hash_match"
        ]:
            result[
                "blockers"
            ].append(
                "AKBNK_ATTACHMENT_HASH_MISMATCH"
            )

        if not result[
            "pdf_magic"
        ]:
            result[
                "blockers"
            ].append(
                "AKBNK_ATTACHMENT_NOT_PDF"
            )

        if (
            result[
                "hash_match"
            ]
            and result[
                "pdf_magic"
            ]
        ):
            NORMALIZED_PDF.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copyfile(
                SOURCE_MISNAMED,
                NORMALIZED_PDF,
            )

            result[
                "normalized_copy_written"
            ] = True

            normalized_hash = _sha256(
                NORMALIZED_PDF
            )

            if (
                normalized_hash
                != EXPECTED_SHA256
            ):
                result[
                    "blockers"
                ].append(
                    "NORMALIZED_PDF_HASH_MISMATCH"
                )

            else:
                (
                    text,
                    page_count,
                    engine,
                    errors,
                ) = _extract_text(
                    NORMALIZED_PDF
                )

                result[
                    "extraction_engine"
                ] = engine

                result[
                    "page_count"
                ] = page_count

                result[
                    "text_char_count"
                ] = len(text)

                result[
                    "extraction_errors"
                ] = errors

                if text.strip():
                    TEXT_OUTPUT.write_text(
                        text,
                        encoding="utf-8",
                    )

                    evidence = (
                        _term_evidence(
                            text
                        )
                    )

                    result[
                        "term_evidence"
                    ] = evidence

                    result[
                        "metric_family_present_count"
                    ] = sum(
                        1
                        for row
                        in evidence.values()
                        if row[
                            "present"
                        ]
                    )

                    result[
                        "evidence_snippets"
                    ] = _snippet_rows(
                        text
                    )

                    result[
                        "financial_text_ready"
                    ] = (
                        result[
                            "metric_family_present_count"
                        ]
                        >= 5
                    )

                    if result[
                        "financial_text_ready"
                    ]:
                        result[
                            "status"
                        ] = "PASS"

                    else:
                        result[
                            "blockers"
                        ].append(
                            "BANK_FINANCIAL_TEXT_COVERAGE_INSUFFICIENT"
                        )

                else:
                    result[
                        "blockers"
                    ].append(
                        "PDF_TEXT_EXTRACTION_EMPTY"
                    )

    if (
        not result[
            "financial_text_ready"
        ]
        and not result[
            "blockers"
        ]
    ):
        result[
            "blockers"
        ].append(
            "BANK_FINANCIAL_PDF_TEXT_NOT_READY"
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
        f"ACTUAL_SHA256={result['actual_sha256']}"
    )
    print(
        f"HASH_MATCH={result['hash_match']}"
    )
    print(
        f"PDF_MAGIC={result['pdf_magic']}"
    )
    print(
        "NORMALIZED_COPY_WRITTEN="
        f"{result['normalized_copy_written']}"
    )
    print(
        "NORMALIZED_PDF_PATH="
        f"{result['normalized_pdf_path']}"
    )
    print(
        "EXTRACTION_ENGINE="
        f"{result['extraction_engine']}"
    )
    print(
        f"PAGE_COUNT={result['page_count']}"
    )
    print(
        "TEXT_CHAR_COUNT="
        f"{result['text_char_count']}"
    )
    print(
        "METRIC_FAMILY_PRESENT_COUNT="
        f"{result['metric_family_present_count']}"
    )

    for metric, row in (
        result[
            "term_evidence"
        ].items()
    ):
        print(
            f"TERM_{metric.upper()}_PRESENT="
            f"{row['present']}"
        )

    print(
        "FINANCIAL_TEXT_READY="
        f"{result['financial_text_ready']}"
    )
    print(
        "BANK_METRIC_MAPPING_READY=False"
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
        "SOURCE_BYTES_MUTATED=NO"
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
        "AKBNK_KAP_PDF_EVIDENCE_NORMALIZATION_TEXT_EXTRACTION_V1=PASS"
    )


if __name__ == "__main__":
    main()
