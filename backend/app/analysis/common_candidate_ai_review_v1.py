"""Read-only Gemini review for the common final candidate list (Sprint-2 V1)."""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from backend.app.market_context.ai_provider import (
    AIProviderConfig,
    AIProviderError,
    build_provider,
)

REVIEW_FIELDS = (
    "summary",
    "positive_factors",
    "risk_factors",
    "stock_specific_risks",
    "aligned_points",
    "conflicting_points",
    "watch_items",
)


def _value(item: object, name: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _evidence_payload(item: object) -> dict[str, str]:
    return {
        "source": _text(_value(item, "source")),
        "horizon": _text(_value(item, "horizon")),
        "status": _text(_value(item, "status")),
        "reason": _text(_value(item, "reason")),
    }


def build_common_candidate_review_prompt(candidate: object) -> str:
    """Build a bounded prompt from the existing candidate contract only."""
    symbol = _text(_value(candidate, "symbol")).upper()
    if not symbol:
        raise ValueError("candidate symbol is required")

    evidence = _value(candidate, "evidence", ()) or ()
    reasons = _value(candidate, "reasons", ()) or ()

    payload = {
        "symbol": symbol,
        "sources": list(_value(candidate, "sources", ()) or ()),
        "horizons": list(_value(candidate, "horizons", ()) or ()),
        "evidence": [_evidence_payload(item) for item in evidence],
        "priority": _value(candidate, "priority"),
        "technical_score": _value(candidate, "technical_score"),
        "volume_ratio": _value(candidate, "volume_ratio"),
        "risk_reward": _value(candidate, "risk_reward"),
        "entry_readiness": _text(_value(candidate, "entry_readiness")),
        "data_status": _text(_value(candidate, "data_status")),
        "reasons": list(reasons),
    }

    context = json.dumps(payload, ensure_ascii=False, default=str)
    return (
        "Task: Review this BIST candidate using only the supplied evidence.\n"
        "Eksik fiyat, hacim, tarih veya gösterge değerlerini tahmin etme. "
        "Eksik verileri açıkça belirt.\n"
        "Yeni puan veya aday sıralaması üretme. AL, SAT, tut, pozisyon büyüklüğü veya emir önerme. Do not recommend "
        "buying, selling, holding, position sizing, or placing orders. "
        "This review grants no trading authority.\n"
        "Return only the existing JSON fields: summary, positive_factors, "
        "risk_factors, stock_specific_risks, aligned_points, "
        "conflicting_points, watch_items. The summary must be a string; "
        "all other fields must be lists of strings.\n"
        "Candidate data:\n"
        f"{context}"
    )


def validate_common_candidate_review(output: object) -> dict[str, Any]:
    if not isinstance(output, Mapping):
        raise ValueError("AI output must be a JSON object")

    result = dict(output)
    if set(result) != set(REVIEW_FIELDS):
        raise ValueError("AI output fields do not match the review contract")

    if not isinstance(result["summary"], str):
        raise ValueError("summary must be a string")

    for field in REVIEW_FIELDS[1:]:
        value = result[field]
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise ValueError(f"{field} must be a list of strings")

    return result


def evaluate_common_candidate_ai_review(
    candidate: object,
    *,
    config: AIProviderConfig | None = None,
    provider: object | None = None,
) -> dict[str, Any]:
    """Evaluate one candidate without changing ranking or trade decisions."""
    symbol = _text(_value(candidate, "symbol")).upper()
    if not symbol:
        return {
            "status": "rejected",
            "reason": "candidate_symbol_missing",
            "automatic_trade_authority": "NONE",
        }

    try:
        prompt = build_common_candidate_review_prompt(candidate)
        active_provider = provider or build_provider(config or AIProviderConfig.from_environment())
        provider_result = active_provider.evaluate(prompt)
        review = validate_common_candidate_review(provider_result.output)
        return {
            "status": "accepted",
            "symbol": symbol,
            "provider": _text(provider_result.provider),
            "model": _text(provider_result.model),
            "review": review,
            "automatic_trade_authority": "NONE",
        }
    except AIProviderError as exc:
        return {
            "status": "provider_error",
            "symbol": symbol,
            "reason": str(exc),
            "automatic_trade_authority": "NONE",
        }
    except (TypeError, ValueError, AttributeError) as exc:
        return {
            "status": "rejected",
            "symbol": symbol,
            "reason": str(exc),
            "automatic_trade_authority": "NONE",
        }