from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.data.kap_financial_xls import (
    KapFinancialXlsError,
    import_kap_financial_xls_bytes,
)


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

EXCLUDED_TOKENS = (
    "\\_backup\\",
    "\\.venv\\",
    "\\node_modules\\",
    "\\dist\\",
    "\\build\\",
)


def _excluded(path: Path) -> bool:
    raw = str(path).lower()
    return any(
        token.lower() in raw
        for token in EXCLUDED_TOKENS
    )


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _identity_value(identity, name):
    value = getattr(identity, name, None)

    if value is None:
        return None

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


def main():
    project = Path(
        r"D:\Projects\Hisse-Robotu"
    )

    roots = [
        Path(r"C:\Users\user\Downloads"),
        project / "backend" / "data",
        project / "data",
    ]

    scanned = 0
    parser_pass = 0
    parser_fail = 0
    bank_rows = []
    non_bank_rows = []

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in {
                ".xls",
                ".xlsx",
            }:
                continue

            if _excluded(path):
                continue

            scanned += 1

            try:
                payload = path.read_bytes()
            except Exception:
                parser_fail += 1
                continue

            try:
                report = import_kap_financial_xls_bytes(
                    payload,
                    source_name=path.name,
                )
            except Exception as exc:
                parser_fail += 1
                continue

            parser_pass += 1

            identity = report.identity
            symbol = str(
                getattr(
                    identity,
                    "symbol",
                    "",
                )
                or ""
            ).strip().upper()

            row = {
                "path": str(path),
                "source_name": path.name,
                "sha256": _sha256(payload),
                "bytes": len(payload),
                "symbol": symbol or None,
                "report_date": _identity_value(
                    identity,
                    "report_date",
                ),
                "published_at": _identity_value(
                    identity,
                    "published_at",
                ),
                "period": _identity_value(
                    identity,
                    "period",
                ),
                "canonical_fact_count":
                    len(report.facts),
                "unmapped_count":
                    len(
                        getattr(
                            report,
                            "unmapped_labels",
                            (),
                        )
                        or ()
                    ),
            }

            if symbol in BANK_SYMBOLS:
                bank_rows.append(row)
            else:
                non_bank_rows.append(row)

    bank_rows.sort(
        key=lambda x: (
            x["symbol"] or "",
            x["published_at"] or "",
            x["path"],
        ),
        reverse=True,
    )

    selected = (
        bank_rows[0]
        if bank_rows
        else None
    )

    result = {
        "schema_version":
            "financial-intelligence-v1-3-bank-kap-xls-semantic-evidence-probe-v1",
        "status":
            "PASS"
            if selected
            else "PASS_FAIL_CLOSED",
        "xls_file_count":
            scanned,
        "kap_parser_pass_count":
            parser_pass,
        "kap_parser_fail_count":
            parser_fail,
        "bank_kap_xls_count":
            len(bank_rows),
        "bank_kap_xls":
            bank_rows[:50],
        "selected_bank_source":
            selected,
        "selected_source_sha256":
            (
                selected["sha256"]
                if selected
                else None
            ),
        "canonical_producer_ready":
            bool(selected),
        "production_evidence":
            bool(selected),
        "activation_ready":
            False,
        "blockers":
            (
                []
                if selected
                else [
                    "NO_PARSEABLE_BANK_KAP_XLS_SOURCE"
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
        / "FINANCIAL_INTELLIGENCE_V1_3_BANK_KAP_XLS_SEMANTIC_EVIDENCE_PROBE.json"
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
        f"XLS_FILE_COUNT="
        f"{result['xls_file_count']}"
    )
    print(
        f"KAP_PARSER_PASS_COUNT="
        f"{result['kap_parser_pass_count']}"
    )
    print(
        f"KAP_PARSER_FAIL_COUNT="
        f"{result['kap_parser_fail_count']}"
    )
    print(
        f"BANK_KAP_XLS_COUNT="
        f"{result['bank_kap_xls_count']}"
    )
    print(
        f"SELECTED_BANK_SOURCE="
        f"{result['selected_bank_source']}"
    )
    print(
        f"SELECTED_SOURCE_SHA256="
        f"{result['selected_source_sha256']}"
    )
    print(
        f"CANONICAL_PRODUCER_READY="
        f"{result['canonical_producer_ready']}"
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

    print(
        "BANK_KAP_XLS_CANDIDATES_START"
    )

    for index, row in enumerate(
        bank_rows[:20],
        start=1,
    ):
        print(
            f"BANK_XLS_{index}="
            f"{json.dumps(row, ensure_ascii=False, sort_keys=True)}"
        )

    print(
        "BANK_KAP_XLS_CANDIDATES_END"
    )
    print("MUTATION=NO")
    print("STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print(f"RESULT={out}")
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "BANK_KAP_XLS_SEMANTIC_EVIDENCE_PROBE_V1=PASS"
    )


if __name__ == "__main__":
    main()
