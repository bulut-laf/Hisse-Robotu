from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .analysis_engine import FundAnalysisClass, FundAnalysisResult


class FundCanonicalResultStoreError(RuntimeError):
    pass


def _default_path() -> Path:
    backend_root = Path(__file__).resolve().parents[2]
    return backend_root / "data" / "funds" / "canonical_analysis_results.json"


def save_last_good_fund_analysis_results(
    results: Iterable[FundAnalysisResult],
    *,
    path: Path | None = None,
) -> int:
    items = tuple(results)
    if not items:
        raise FundCanonicalResultStoreError("EMPTY_CANONICAL_RESULT_SET")
    target = path or _default_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "results": [
            {
                "canonical_fund_id": item.canonical_fund_id,
                "category_id": item.category_id,
                "classification": item.classification.value,
                "class_label": item.class_label,
                "positive_families": list(item.positive_families),
                "neutral_families": list(item.neutral_families),
                "caution_families": list(item.caution_families),
                "unavailable_families": list(item.unavailable_families),
                "eligibility_reason": item.eligibility_reason,
                "explanation": item.explanation,
                "automatic_trade_authority": item.automatic_trade_authority,
                "forced_fill": item.forced_fill,
                "engine_version": item.engine_version,
            }
            for item in items
        ],
    }
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)
    return len(items)


def load_last_good_fund_analysis_results(
    *,
    path: Path | None = None,
) -> tuple[FundAnalysisResult, ...]:
    target = path or _default_path()
    if not target.exists():
        return ()
    try:
        payload = json.loads(target.read_text(encoding="utf-8-sig"))
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise ValueError("results must be a list")
        items = []
        for raw in raw_results:
            items.append(
                FundAnalysisResult(
                    canonical_fund_id=str(raw["canonical_fund_id"]),
                    category_id=raw.get("category_id"),
                    classification=FundAnalysisClass(str(raw["classification"])),
                    class_label=str(raw["class_label"]),
                    positive_families=tuple(raw.get("positive_families", ())),
                    neutral_families=tuple(raw.get("neutral_families", ())),
                    caution_families=tuple(raw.get("caution_families", ())),
                    unavailable_families=tuple(raw.get("unavailable_families", ())),
                    eligibility_reason=str(raw["eligibility_reason"]),
                    explanation=str(raw["explanation"]),
                    automatic_trade_authority=str(raw.get("automatic_trade_authority", "NONE")),
                    forced_fill=bool(raw.get("forced_fill", False)),
                    engine_version=str(raw.get("engine_version", "fund-analysis-v1")),
                )
            )
        return tuple(items)
    except Exception as exc:
        raise FundCanonicalResultStoreError(
            f"CANONICAL_RESULT_STORE_READ_FAILED:{exc}"
        ) from exc
