from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.analysis.financial_intelligence_insurance_canonical_adapter import (
    adapt_insurance_canonical_input,
)
from app.analysis.financial_intelligence_insurance_scoring_engine import (
    score_insurance_model,
)


EXCLUDED_NAME_TOKENS = (
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
)


def _load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def _iter_candidate_records(fi_dir: Path):
    for path in sorted(fi_dir.rglob("*.json")):
        lower_name = path.name.lower()

        if any(
            token in lower_name
            for token in EXCLUDED_NAME_TOKENS
        ):
            continue

        try:
            data = _load_json(path)
        except Exception:
            continue

        records: list[dict[str, Any]] = []

        if isinstance(data, dict):
            records.append(data)

            for key in (
                "data",
                "records",
                "items",
                "results",
            ):
                value = data.get(key)

                if isinstance(value, list):
                    records.extend(
                        item
                        for item in value
                        if isinstance(item, dict)
                    )

        elif isinstance(data, list):
            records.extend(
                item
                for item in data
                if isinstance(item, dict)
            )

        for record in records:
            if (
                str(
                    record.get("sector_model")
                    or ""
                )
                .strip()
                .upper()
                != "INSURANCE"
            ):
                continue

            if not isinstance(
                record.get("canonical_facts"),
                dict,
            ):
                continue

            if not str(
                record.get("as_of")
                or ""
            ).strip():
                continue

            if not str(
                record.get("publication_date")
                or ""
            ).strip():
                continue

            yield path, record


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--project-root",
        default=r"D:\Projects\Hisse-Robotu",
    )

    parser.add_argument(
        "--source-path",
        default=None,
    )

    args = parser.parse_args()

    root = Path(args.project_root)

    fi_dir = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
    )

    fi_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    out = (
        fi_dir
        / "FINANCIAL_INTELLIGENCE_V1_2_"
          "INSURANCE_REAL_DATA_INTAKE_GATE.json"
    )

    candidates: list[
        tuple[Path, dict[str, Any]]
    ] = []

    if args.source_path:
        source = Path(args.source_path)

        if not source.exists():
            raise FileNotFoundError(source)

        if source.suffix.lower() != ".json":
            result = {
                "schema_version":
                    "financial-intelligence-v1-2-"
                    "insurance-real-data-intake-gate-v1",
                "status": "PASS_FAIL_CLOSED",
                "candidate_count": 0,
                "accepted_count": 0,
                "selected_symbol": None,
                "selected_source": str(source),
                "canonical_input_ready": False,
                "scoring_ready": False,
                "blockers": [
                    "INSURANCE_SOURCE_FORMAT_NOT_YET_SUPPORTED"
                ],
                "production_evidence": False,
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
                "STATUS=PASS_FAIL_CLOSED"
            )
            print(
                "CANDIDATE_COUNT=0"
            )
            print(
                "ACCEPTED_COUNT=0"
            )
            print(
                "SELECTED_SYMBOL=None"
            )
            print(
                f"SELECTED_SOURCE={source}"
            )
            print(
                "CANONICAL_INPUT_READY=False"
            )
            print(
                "SCORING_READY=False"
            )
            print(
                "BLOCKERS=['INSURANCE_SOURCE_FORMAT_NOT_YET_SUPPORTED']"
            )
            print(
                "PRODUCTION_EVIDENCE=False"
            )
            print(
                f"RESULT={out}"
            )
            print(
                "FINANCIAL_INTELLIGENCE_V1_2_"
                "INSURANCE_REAL_DATA_INTAKE_GATE_V1=PASS"
            )
            return

        data = _load_json(source)

        if isinstance(data, dict):
            candidates.append(
                (source, data)
            )

    else:
        candidates.extend(
            _iter_candidate_records(fi_dir)
        )

    accepted = []
    rejected = []

    for source, record in candidates:
        adapted = (
            adapt_insurance_canonical_input(
                record
            )
        )

        if adapted.status != "PASS":
            rejected.append({
                "source": str(source),
                "symbol": adapted.symbol,
                "blocker": adapted.blocker,
            })
            continue

        assert adapted.payload is not None

        scored = score_insurance_model(
            adapted.payload
        )

        if scored.status != "PASS":
            rejected.append({
                "source": str(source),
                "symbol": adapted.symbol,
                "blocker": scored.blocker,
            })
            continue

        accepted.append({
            "source": str(source),
            "symbol": adapted.symbol,
            "as_of": adapted.as_of,
            "publication_date":
                adapted.publication_date,
            "score": scored.total_score,
        })

    if not accepted:
        blocker = (
            "NO_REAL_INSURANCE_SOURCE"
            if not candidates
            else
            "NO_INSURANCE_SOURCE_PASSED_CANONICAL_GATE"
        )

        result = {
            "schema_version":
                "financial-intelligence-v1-2-"
                "insurance-real-data-intake-gate-v1",
            "status": "PASS_FAIL_CLOSED",
            "candidate_count":
                len(candidates),
            "accepted_count": 0,
            "selected_symbol": None,
            "selected_source": None,
            "canonical_input_ready": False,
            "scoring_ready": False,
            "blockers": [blocker],
            "rejected": rejected,
            "production_evidence": False,
        }

    else:
        accepted.sort(
            key=lambda x: (
                x["symbol"] or "",
                x["source"],
            )
        )

        selected = accepted[0]

        result = {
            "schema_version":
                "financial-intelligence-v1-2-"
                "insurance-real-data-intake-gate-v1",
            "status": "PASS",
            "candidate_count":
                len(candidates),
            "accepted_count":
                len(accepted),
            "selected_symbol":
                selected["symbol"],
            "selected_source":
                selected["source"],
            "as_of":
                selected["as_of"],
            "publication_date":
                selected["publication_date"],
            "canonical_input_ready": True,
            "scoring_ready": True,
            "score":
                selected["score"],
            "blockers": [],
            "accepted": accepted,
            "rejected": rejected,
            "production_evidence": True,
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
        f"CANDIDATE_COUNT="
        f"{result['candidate_count']}"
    )
    print(
        f"ACCEPTED_COUNT="
        f"{result['accepted_count']}"
    )
    print(
        f"SELECTED_SYMBOL="
        f"{result['selected_symbol']}"
    )
    print(
        f"SELECTED_SOURCE="
        f"{result['selected_source']}"
    )
    print(
        f"CANONICAL_INPUT_READY="
        f"{result['canonical_input_ready']}"
    )
    print(
        f"SCORING_READY="
        f"{result['scoring_ready']}"
    )
    print(
        f"BLOCKERS="
        f"{result['blockers']}"
    )
    print(
        f"PRODUCTION_EVIDENCE="
        f"{result['production_evidence']}"
    )
    print(
        f"RESULT={out}"
    )
    print(
        "FINANCIAL_INTELLIGENCE_V1_2_"
        "INSURANCE_REAL_DATA_INTAKE_GATE_V1=PASS"
    )


if __name__ == "__main__":
    main()
