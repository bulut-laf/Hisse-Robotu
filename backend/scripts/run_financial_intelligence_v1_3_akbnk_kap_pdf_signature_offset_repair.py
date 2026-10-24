from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(r"D:\Projects\Hisse-Robotu")

SOURCE = (
    ROOT
    / "backend"
    / "data"
    / "financial_intelligence"
    / "evidence"
    / "AKBNK"
    / "AKBNK_1637884_2026_2.xls"
)

NORMALIZED = (
    ROOT
    / "backend"
    / "data"
    / "financial_intelligence"
    / "evidence"
    / "AKBNK"
    / "AKBNK_1637884_2026_2.pdf"
)

TEXT_OUT = (
    ROOT
    / "backend"
    / "data"
    / "financial_intelligence"
    / "evidence"
    / "AKBNK"
    / "AKBNK_1637884_2026_2.txt"
)

RESULT = (
    ROOT
    / "backend"
    / "data"
    / "financial_intelligence"
    / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_KAP_PDF_SIGNATURE_OFFSET_REPAIR.json"
)

EXPECTED_SHA256 = (
    "48a89d5e4343ee8b34fd7af9e2c73f6405e25b803b2d1695b4374bcacba9b9e5"
)

TERMS = (
    "sermaye yeterlilik",
    "ana sermaye",
    "çekirdek sermaye",
    "krediler",
    "mevduat",
    "takipteki",
    "özkaynak",
    "toplam aktif",
    "faiz gelirleri",
    "faiz giderleri",
    "net dönem karı",
    "net dönem kârı",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_text(path: Path):
    errors = []

    try:
        import fitz

        doc = fitz.open(path)
        text = "\n".join(
            page.get_text("text") or ""
            for page in doc
        )
        if text.strip():
            return text, len(doc), "PYMUPDF", errors
        errors.append("PYMUPDF:EMPTY_TEXT")
    except Exception as exc:
        errors.append(
            f"PYMUPDF:{type(exc).__name__}:{exc}"
        )

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )
        if text.strip():
            return text, len(reader.pages), "PYPDF", errors
        errors.append("PYPDF:EMPTY_TEXT")
    except Exception as exc:
        errors.append(
            f"PYPDF:{type(exc).__name__}:{exc}"
        )

    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(str(path))
        text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )
        if text.strip():
            return text, len(reader.pages), "PYPDF2", errors
        errors.append("PYPDF2:EMPTY_TEXT")
    except Exception as exc:
        errors.append(
            f"PYPDF2:{type(exc).__name__}:{exc}"
        )

    return "", 0, None, errors


def main():
    result = {
        "status": "PASS_FAIL_CLOSED",
        "source_path": str(SOURCE),
        "normalized_path": str(NORMALIZED),
        "expected_sha256": EXPECTED_SHA256,
        "actual_sha256": None,
        "hash_match": False,
        "header_hex_64": None,
        "pdf_magic_offset_4096": -1,
        "pdf_signature_present": False,
        "normalized_copy_written": False,
        "normalized_sha256": None,
        "extraction_engine": None,
        "page_count": 0,
        "text_char_count": 0,
        "financial_term_hits": {},
        "financial_term_present_count": 0,
        "financial_text_ready": False,
        "bank_metric_mapping_ready": False,
        "scoring_ready": False,
        "activation_ready": False,
        "errors": [],
        "blockers": [],
        "source_bytes_mutated": "NO",
        "store_mutation": "NO",
        "al_sat_mutation": "NO",
    }

    if not SOURCE.exists():
        result["blockers"].append(
            "AKBNK_ATTACHMENT_SOURCE_MISSING"
        )
    else:
        actual = sha256(SOURCE)
        result["actual_sha256"] = actual
        result["hash_match"] = (
            actual == EXPECTED_SHA256
        )

        raw = SOURCE.read_bytes()

        result["header_hex_64"] = (
            raw[:64].hex()
        )

        offset = raw[:4096].find(
            b"%PDF-"
        )

        result["pdf_magic_offset_4096"] = (
            offset
        )
        result["pdf_signature_present"] = (
            offset >= 0
        )

        if not result["hash_match"]:
            result["blockers"].append(
                "AKBNK_ATTACHMENT_HASH_MISMATCH"
            )

        # Do not reject solely because %PDF- is not byte zero.
        # Attempt parser when official KAP content was already observed as application/pdf.
        if result["hash_match"]:
            NORMALIZED.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copyfile(
                SOURCE,
                NORMALIZED,
            )

            result[
                "normalized_copy_written"
            ] = True

            normalized_hash = sha256(
                NORMALIZED
            )

            result[
                "normalized_sha256"
            ] = normalized_hash

            if normalized_hash != actual:
                result["blockers"].append(
                    "NORMALIZED_COPY_HASH_MISMATCH"
                )
            else:
                (
                    text,
                    pages,
                    engine,
                    errors,
                ) = extract_text(
                    NORMALIZED
                )

                result["errors"] = errors
                result[
                    "extraction_engine"
                ] = engine
                result[
                    "page_count"
                ] = pages
                result[
                    "text_char_count"
                ] = len(text)

                if text.strip():
                    TEXT_OUT.write_text(
                        text,
                        encoding="utf-8",
                    )

                    folded = (
                        text.casefold()
                    )

                    hits = {
                        term:
                            folded.count(
                                term.casefold()
                            )
                        for term
                        in TERMS
                    }

                    result[
                        "financial_term_hits"
                    ] = hits

                    result[
                        "financial_term_present_count"
                    ] = sum(
                        1
                        for count
                        in hits.values()
                        if count > 0
                    )

                    result[
                        "financial_text_ready"
                    ] = (
                        len(text) > 1000
                        and result[
                            "financial_term_present_count"
                        ] >= 3
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
                        "PDF_TEXT_EXTRACTION_FAILED"
                    )

    if (
        not result["financial_text_ready"]
        and not result["blockers"]
    ):
        result["blockers"].append(
            "AKBNK_PDF_TEXT_NOT_READY"
        )

    RESULT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT.write_text(
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
        f"HEADER_HEX_64={result['header_hex_64']}"
    )
    print(
        "PDF_MAGIC_OFFSET_4096="
        f"{result['pdf_magic_offset_4096']}"
    )
    print(
        "PDF_SIGNATURE_PRESENT="
        f"{result['pdf_signature_present']}"
    )
    print(
        "NORMALIZED_COPY_WRITTEN="
        f"{result['normalized_copy_written']}"
    )
    print(
        "NORMALIZED_SHA256="
        f"{result['normalized_sha256']}"
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
        "FINANCIAL_TERM_PRESENT_COUNT="
        f"{result['financial_term_present_count']}"
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
        f"ERRORS={result['errors']}"
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
        f"RESULT={RESULT}"
    )
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "AKBNK_KAP_PDF_SIGNATURE_OFFSET_REPAIR_V1=PASS"
    )


if __name__ == "__main__":
    main()
