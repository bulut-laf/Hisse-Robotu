from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from app.analysis.financial_intelligence_bank_model_contract import (
    BANK_COMPONENTS,
    BANK_REQUIRED_METRICS,
    validate_bank_model_input,
)


@dataclass(frozen=True)
class BankCanonicalAdapterResult:
    status: str
    symbol: str | None
    as_of: str | None
    publication_date: str | None
    payload: Mapping[str, Mapping[str, float]] | None
    blocker: str | None


def _parse_iso_date(value: object, field: str) -> date:
    text = str(value or "").strip()

    if not text:
        raise ValueError(f"{field}_MISSING")

    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"{field}_INVALID:{text}"
        ) from exc


def _number(value: Any, key: str) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError(
            f"BANK_CANONICAL_METRIC_MISSING:{key}"
        )

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"BANK_CANONICAL_METRIC_NOT_NUMERIC:{key}"
        ) from exc


def adapt_bank_canonical_input(
    record: Mapping[str, Any],
) -> BankCanonicalAdapterResult:

    symbol = str(
        record.get("symbol") or ""
    ).strip().upper()

    if not symbol:
        return BankCanonicalAdapterResult(
            status="BLOCKED",
            symbol=None,
            as_of=None,
            publication_date=None,
            payload=None,
            blocker="SYMBOL_MISSING",
        )

    sector_model = str(
        record.get("sector_model") or ""
    ).strip().upper()

    if sector_model != "BANK":
        return BankCanonicalAdapterResult(
            status="BLOCKED",
            symbol=symbol,
            as_of=None,
            publication_date=None,
            payload=None,
            blocker=(
                "SECTOR_MODEL_MISMATCH:"
                + (sector_model or "MISSING")
            ),
        )

    try:
        as_of_date = _parse_iso_date(
            record.get("as_of"),
            "AS_OF",
        )

        publication = _parse_iso_date(
            record.get("publication_date"),
            "PUBLICATION_DATE",
        )

    except ValueError as exc:
        return BankCanonicalAdapterResult(
            status="BLOCKED",
            symbol=symbol,
            as_of=None,
            publication_date=None,
            payload=None,
            blocker=str(exc),
        )

    if publication > as_of_date:
        return BankCanonicalAdapterResult(
            status="BLOCKED",
            symbol=symbol,
            as_of=as_of_date.isoformat(),
            publication_date=publication.isoformat(),
            payload=None,
            blocker="FUTURE_PUBLICATION_FORBIDDEN",
        )

    facts = record.get("canonical_facts")

    if not isinstance(facts, Mapping):
        return BankCanonicalAdapterResult(
            status="BLOCKED",
            symbol=symbol,
            as_of=as_of_date.isoformat(),
            publication_date=publication.isoformat(),
            payload=None,
            blocker="CANONICAL_FACTS_MISSING",
        )

    payload: dict[str, dict[str, float]] = {}

    try:
        for component in BANK_COMPONENTS:

            payload[component] = {}

            for metric in BANK_REQUIRED_METRICS[
                component
            ]:

                canonical_key = (
                    f"{component}.{metric}"
                )

                if canonical_key not in facts:
                    raise ValueError(
                        "BANK_CANONICAL_METRIC_MISSING:"
                        + canonical_key
                    )

                payload[component][metric] = _number(
                    facts[canonical_key],
                    canonical_key,
                )

    except ValueError as exc:
        return BankCanonicalAdapterResult(
            status="BLOCKED",
            symbol=symbol,
            as_of=as_of_date.isoformat(),
            publication_date=publication.isoformat(),
            payload=None,
            blocker=str(exc),
        )

    validation = validate_bank_model_input(
        payload
    )

    if not validation.ready_for_scoring:
        return BankCanonicalAdapterResult(
            status="BLOCKED",
            symbol=symbol,
            as_of=as_of_date.isoformat(),
            publication_date=publication.isoformat(),
            payload=None,
            blocker=validation.blocker,
        )

    return BankCanonicalAdapterResult(
        status="PASS",
        symbol=symbol,
        as_of=as_of_date.isoformat(),
        publication_date=publication.isoformat(),
        payload=payload,
        blocker=None,
    )


__all__ = [
    "BankCanonicalAdapterResult",
    "adapt_bank_canonical_input",
]
