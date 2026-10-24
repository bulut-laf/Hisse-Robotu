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

def save_last_good_fund_analysis_results(results: Iterable[FundAnalysisResult], *, path: Path | None = None) -> int:
    items = tuple(results)
    if not items:
        raise FundCanonicalResultStoreError("EMPTY_CANONICAL_RESULT_SET")
    target = path or _default_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "results": [
        {
            "canonical_fund_id": i.canonical_fund_id,
            "category_id": i.category_id,
            "classification": i.classification.value,
            "class_label": i.class_label,
            "positive_families": list(i.positive_families),
            "neutral_families": list(i.neutral_families),
            "caution_families": list(i.caution_families),
            "unavailable_families": list(i.unavailable_families),
            "eligibility_reason": i.eligibility_reason,
            "explanation": i.explanation,
            "automatic_trade_authority": i.automatic_trade_authority,
            "forced_fill": i.forced_fill,
            "engine_version": i.engine_version,
        } for i in items
    ]}
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)
    return len(items)

def load_last_good_fund_analysis_results(*, path: Path | None = None) -> tuple[FundAnalysisResult, ...]:
    target = path or _default_path()
    if not target.exists():
        return ()
    try:
        payload = json.loads(target.read_text(encoding="utf-8-sig"))
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise ValueError("results must be a list")
        out = []
        for r in raw_results:
            out.append(FundAnalysisResult(
                canonical_fund_id=str(r["canonical_fund_id"]),
                category_id=r.get("category_id"),
                classification=FundAnalysisClass(str(r["classification"])),
                class_label=str(r["class_label"]),
                positive_families=tuple(r.get("positive_families", ())),
                neutral_families=tuple(r.get("neutral_families", ())),
                caution_families=tuple(r.get("caution_families", ())),
                unavailable_families=tuple(r.get("unavailable_families", ())),
                eligibility_reason=str(r["eligibility_reason"]),
                explanation=str(r["explanation"]),
                automatic_trade_authority=str(r.get("automatic_trade_authority", "NONE")),
                forced_fill=bool(r.get("forced_fill", False)),
                engine_version=str(r.get("engine_version", "fund-analysis-v1")),
            ))
        return tuple(out)
    except Exception as exc:
        raise FundCanonicalResultStoreError(f"CANONICAL_RESULT_STORE_READ_FAILED:{exc}") from exc
