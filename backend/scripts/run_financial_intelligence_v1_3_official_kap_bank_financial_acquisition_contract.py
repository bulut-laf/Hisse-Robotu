from __future__ import annotations

import ast
import json
from pathlib import Path


TARGET_FILES = (
    r"backend\app\news_center\kap_flow.py",
    r"backend\app\data\kap_financial_xls.py",
    r"backend\app\funds\kap_portfolio_auto_ingestion.py",
)

FUNCTION_NAMES = (
    "kap_flow_rows",
    "_default_fetch",
    "_fetch_targeted_fund_disclosures",
    "_validate_disclosures_url",
    "import_kap_financial_xls_bytes",
    "import_kap_financial_xls",
)


def _extract_defs(path: Path, names: set[str]):
    text = path.read_text(
        encoding="utf-8-sig",
        errors="ignore",
    )
    tree = ast.parse(text)
    lines = text.splitlines()

    rows = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        if node.name not in names:
            continue

        start = node.lineno
        end = getattr(
            node,
            "end_lineno",
            node.lineno,
        )

        snippet = "\n".join(
            lines[start - 1:end]
        )

        rows.append({
            "path": str(path),
            "name": node.name,
            "line_start": start,
            "line_end": end,
            "snippet": snippet,
        })

    return rows


def _extract_url_lines(path: Path):
    text = path.read_text(
        encoding="utf-8-sig",
        errors="ignore",
    )

    out = []

    for i, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        folded = line.casefold()

        if (
            "kap.org.tr" in folded
            or "KAP_DISCLOSURES_URL" in line
            or "/tr/api/disclosures" in line
            or "/tr/Bildirim/" in line
        ):
            out.append({
                "path": str(path),
                "line": i,
                "text": line.strip(),
            })

    return out


def main():
    root = Path(
        r"D:\Projects\Hisse-Robotu"
    )

    definitions = []
    url_lines = []
    existing = []

    for rel in TARGET_FILES:
        path = root / rel

        if not path.exists():
            continue

        existing.append(
            str(path)
        )

        definitions.extend(
            _extract_defs(
                path,
                set(FUNCTION_NAMES),
            )
        )

        url_lines.extend(
            _extract_url_lines(
                path
            )
        )

    # Exact contract prerequisites.
    names = {
        row["name"]
        for row in definitions
    }

    required_present = {
        "kap_flow_rows":
            "kap_flow_rows" in names,
        "import_kap_financial_xls_bytes":
            "import_kap_financial_xls_bytes"
            in names,
    }

    endpoint_lines = [
        row
        for row in url_lines
        if (
            "/tr/api/disclosures"
            in row["text"]
            or "KAP_DISCLOSURES_URL"
            in row["text"]
        )
    ]

    detail_lines = [
        row
        for row in url_lines
        if "/tr/Bildirim/" in row["text"]
    ]

    status = (
        "PASS"
        if (
            all(
                required_present.values()
            )
            and endpoint_lines
        )
        else "PASS_FAIL_CLOSED"
    )

    blockers = []

    if not all(
        required_present.values()
    ):
        blockers.append(
            "REQUIRED_KAP_CODE_SEAM_MISSING"
        )

    if not endpoint_lines:
        blockers.append(
            "KAP_DISCLOSURES_ENDPOINT_NOT_FOUND"
        )

    result = {
        "schema_version":
            "financial-intelligence-v1-3-official-kap-bank-financial-acquisition-contract-v1",
        "status":
            status,
        "existing_target_files":
            existing,
        "required_present":
            required_present,
        "definitions":
            definitions,
        "endpoint_lines":
            endpoint_lines,
        "detail_url_lines":
            detail_lines,
        "live_acquisition_ready":
            status == "PASS",
        "production_evidence":
            False,
        "bank_activation_ready":
            False,
        "blockers":
            blockers,
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
        / "FINANCIAL_INTELLIGENCE_V1_3_OFFICIAL_KAP_BANK_FINANCIAL_ACQUISITION_CONTRACT.json"
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
        f"EXISTING_TARGET_FILES="
        f"{len(existing)}"
    )
    print(
        f"REQUIRED_PRESENT="
        f"{result['required_present']}"
    )
    print(
        f"ENDPOINT_LINE_COUNT="
        f"{len(endpoint_lines)}"
    )
    print(
        f"DETAIL_URL_LINE_COUNT="
        f"{len(detail_lines)}"
    )
    print(
        f"LIVE_ACQUISITION_READY="
        f"{result['live_acquisition_ready']}"
    )
    print(
        "PRODUCTION_EVIDENCE=False"
    )
    print(
        "BANK_ACTIVATION_READY=False"
    )
    print(
        f"BLOCKERS={result['blockers']}"
    )

    print(
        "ENDPOINT_LINES_START"
    )
    for i, row in enumerate(
        endpoint_lines,
        start=1,
    ):
        print(
            f"ENDPOINT_{i}="
            f"{json.dumps(row, ensure_ascii=False, sort_keys=True)}"
        )
    print(
        "ENDPOINT_LINES_END"
    )

    print(
        "DEFINITIONS_START"
    )
    for i, row in enumerate(
        definitions,
        start=1,
    ):
        compact = {
            "path":
                row["path"],
            "name":
                row["name"],
            "line_start":
                row["line_start"],
            "line_end":
                row["line_end"],
        }
        print(
            f"DEF_{i}="
            f"{json.dumps(compact, ensure_ascii=False, sort_keys=True)}"
        )
    print(
        "DEFINITIONS_END"
    )

    print(
        f"RESULT={out}"
    )
    print("MUTATION=NO")
    print("STORE_MUTATION=NO")
    print("AL_SAT_MUTATION=NO")
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "OFFICIAL_KAP_BANK_FINANCIAL_ACQUISITION_CONTRACT_V1=PASS"
    )


if __name__ == "__main__":
    main()
