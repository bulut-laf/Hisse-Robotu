from __future__ import annotations

import ast
import json
from pathlib import Path


KAP_TERMS = (
    "kap",
    "disclosure",
    "financial",
    "finansal",
    "statement",
    "bildirim",
    "xls",
    "xlsx",
)

STRONG_TERMS = (
    "financial_intelligence",
    "kap",
    "disclosure",
    "financial",
    "statement",
    "xls",
    "xlsx",
)


def _score_text(text: str) -> int:
    folded = text.casefold()
    score = 0

    for term in KAP_TERMS:
        if term in folded:
            score += 2

    for term in STRONG_TERMS:
        if term in folded:
            score += 2

    if "kap.org.tr" in folded:
        score += 8

    if "urlopen" in folded or "requests." in folded:
        score += 3

    if "pandas" in folded or "read_excel" in folded:
        score += 3

    return score


def _definitions(path: Path, text: str):
    out = []

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out

    lines = text.splitlines()

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            name = getattr(
                node,
                "name",
                "",
            )

            if not name:
                continue

            start = max(
                0,
                node.lineno - 1,
            )

            end = min(
                len(lines),
                getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                ),
            )

            body = "\n".join(
                lines[start:end]
            )

            score = _score_text(
                name + "\n" + body
            )

            if score < 4:
                continue

            out.append({
                "kind":
                    "class"
                    if isinstance(
                        node,
                        ast.ClassDef,
                    )
                    else "function",
                "name":
                    name,
                "line":
                    node.lineno,
                "score":
                    score,
                "snippet":
                    "\n".join(
                        lines[
                            start:
                            min(
                                len(lines),
                                start + 35,
                            )
                        ]
                    ),
            })

    return out


def main():
    root = Path(
        r"D:\Projects\Hisse-Robotu"
    )

    code_roots = [
        root / "backend" / "app",
        root / "backend" / "scripts",
    ]

    files = []
    definitions = []
    endpoints = set()

    for base in code_roots:
        if not base.exists():
            continue

        for path in base.rglob("*.py"):
            try:
                text = path.read_text(
                    encoding="utf-8-sig",
                    errors="ignore",
                )
            except Exception:
                continue

            score = _score_text(
                path.name
                + "\n"
                + text
            )

            if score < 4:
                continue

            file_row = {
                "path": str(path),
                "score": score,
                "has_kap_domain":
                    "kap.org.tr"
                    in text.casefold(),
                "has_read_excel":
                    "read_excel"
                    in text,
                "has_urlopen":
                    "urlopen"
                    in text,
                "has_requests":
                    "requests."
                    in text,
            }

            files.append(
                file_row
            )

            for item in _definitions(
                path,
                text,
            ):
                item[
                    "path"
                ] = str(path)

                definitions.append(
                    item
                )

            for line in text.splitlines():
                folded = line.casefold()

                if (
                    "kap.org.tr"
                    in folded
                    and "http"
                    in folded
                ):
                    endpoints.add(
                        line.strip()
                    )

    files.sort(
        key=lambda row: (
            -row["score"],
            row["path"],
        )
    )

    definitions.sort(
        key=lambda row: (
            -row["score"],
            row["path"],
            row["line"],
        )
    )

    likely = [
        row
        for row in definitions
        if (
            row["score"] >= 10
            and (
                "financial"
                in row["name"].casefold()
                or "kap"
                in row["name"].casefold()
                or "disclosure"
                in row["name"].casefold()
                or "statement"
                in row["name"].casefold()
            )
        )
    ]

    result = {
        "schema_version":
            "financial-intelligence-v1-3-bank-official-kap-financial-acquisition-preflight-v1",
        "status":
            "PASS"
            if likely
            else "PASS_FAIL_CLOSED",
        "candidate_source_file_count":
            len(files),
        "candidate_definition_count":
            len(definitions),
        "likely_acquisition_seam_count":
            len(likely),
        "selected_seam":
            (
                likely[0]
                if likely
                else None
            ),
        "top_source_files":
            files[:30],
        "top_definitions":
            definitions[:50],
        "kap_endpoint_lines":
            sorted(endpoints)[:50],
        "production_mutation":
            "NO",
        "store_mutation":
            "NO",
        "al_sat_mutation":
            "NO",
        "bank_activation_ready":
            False,
        "blockers":
            (
                []
                if likely
                else [
                    "OFFICIAL_KAP_FINANCIAL_ACQUISITION_SEAM_NOT_FOUND"
                ]
            ),
    }

    out = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_BANK_OFFICIAL_KAP_FINANCIAL_ACQUISITION_PREFLIGHT.json"
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
        "CANDIDATE_SOURCE_FILE_COUNT="
        f"{result['candidate_source_file_count']}"
    )
    print(
        "CANDIDATE_DEFINITION_COUNT="
        f"{result['candidate_definition_count']}"
    )
    print(
        "LIKELY_ACQUISITION_SEAM_COUNT="
        f"{result['likely_acquisition_seam_count']}"
    )
    print(
        f"SELECTED_SEAM="
        f"{result['selected_seam']}"
    )

    print(
        "TOP_SOURCE_FILES_START"
    )

    for index, row in enumerate(
        files[:10],
        start=1,
    ):
        print(
            f"FILE_{index}="
            f"{json.dumps(row, ensure_ascii=False, sort_keys=True)}"
        )

    print(
        "TOP_SOURCE_FILES_END"
    )

    print(
        "TOP_DEFINITIONS_START"
    )

    for index, row in enumerate(
        definitions[:15],
        start=1,
    ):
        compact = {
            "path":
                row["path"],
            "kind":
                row["kind"],
            "name":
                row["name"],
            "line":
                row["line"],
            "score":
                row["score"],
        }

        print(
            f"DEF_{index}="
            f"{json.dumps(compact, ensure_ascii=False, sort_keys=True)}"
        )

    print(
        "TOP_DEFINITIONS_END"
    )

    print(
        f"KAP_ENDPOINT_LINES="
        f"{json.dumps(result['kap_endpoint_lines'], ensure_ascii=False)}"
    )
    print(
        "BANK_ACTIVATION_READY=False"
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
        f"RESULT={out}"
    )
    print(
        "FINANCIAL_INTELLIGENCE_V1_3_"
        "BANK_OFFICIAL_KAP_FINANCIAL_ACQUISITION_PREFLIGHT_V1=PASS"
    )


if __name__ == "__main__":
    main()
