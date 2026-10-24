from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACT = (
    PROJECT_ROOT
    / "_discovery"
    / "erste_hungary"
    / "f1_f2_f3_f4_evidence_v1_latest.json"
)

REQUIRED_FIELDS = (
    "as_of",
    "automatic_trade_authority",
    "canonical_fund_id",
    "category_id",
    "classification",
    "eligibility_reason",
    "f1_state",
    "f2_state",
    "f3_state",
    "f4_latest_date",
    "f4_previous_date",
    "f4_state",
    "forced_fill",
    "instrument_id",
    "isin",
)

ALLOWED_CLASSIFICATIONS = {"A", "B", "C", "D", "X"}
ALLOWED_STATES = {"POSITIVE", "NEUTRAL", "CAUTION", "UNAVAILABLE"}



def _normalize_evidence_state(value: object) -> str:
    # Normalize enum/string evidence states at the artifact boundary only.
    raw = getattr(value, "value", None)
    if raw is None:
        raw = str(value).strip()
    else:
        raw = str(raw).strip()

    if raw.startswith("EvidenceState."):
        raw = raw.split(".", 1)[1].strip()

    return raw


@dataclass(frozen=True)
class ErsteHungaryEvidenceSurfaceRow:
    as_of: str
    canonical_fund_id: str
    isin: str | None
    instrument_id: str | None
    category_id: str | None
    classification: str
    eligibility_reason: str
    f1_state: str
    f2_state: str
    f3_state: str
    f4_state: str
    f4_latest_date: str | None
    f4_previous_date: str | None
    f5_state: str = "SAFE_UNAVAILABLE"
    automatic_trade_authority: str = "NONE"
    forced_fill: bool = False


def _validate_item(item: Mapping[str, object]) -> None:
    missing = tuple(key for key in REQUIRED_FIELDS if key not in item)
    if missing:
        raise ValueError("MISSING_FIELDS:" + ",".join(missing))

    canonical = str(item["canonical_fund_id"]).strip()
    if not canonical:
        raise ValueError("EMPTY_CANONICAL_FUND_ID")

    classification = str(item["classification"]).strip()
    if classification not in ALLOWED_CLASSIFICATIONS:
        raise ValueError("INVALID_CLASSIFICATION:" + classification)

    for name in ("f1_state", "f2_state", "f3_state", "f4_state"):
        state = _normalize_evidence_state(item[name])
        if state not in ALLOWED_STATES:
            raise ValueError("INVALID_" + name.upper() + ":" + state)

    authority = str(item["automatic_trade_authority"]).strip()
    if authority != "NONE":
        raise ValueError("TRADE_AUTHORITY_NOT_NONE:" + canonical)

    if bool(item["forced_fill"]):
        raise ValueError("FORCED_FILL_TRUE:" + canonical)


def load_erste_hungary_evidence_surface(
    artifact_path: Path | None = None,
) -> tuple[ErsteHungaryEvidenceSurfaceRow, ...]:
    path = Path(artifact_path or DEFAULT_ARTIFACT)
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict):
        records = payload.get("results")
        if records is None:
            records = payload.get("items")
    else:
        records = payload

    if not isinstance(records, list):
        raise ValueError("ARTIFACT_RESULT_LIST_MISSING")

    rows: list[ErsteHungaryEvidenceSurfaceRow] = []
    seen: set[str] = set()

    for raw in records:
        if not isinstance(raw, dict):
            raise ValueError("ARTIFACT_ROW_NOT_OBJECT")

        _validate_item(raw)
        canonical = str(raw["canonical_fund_id"]).strip()

        if canonical in seen:
            raise ValueError("DUPLICATE_CANONICAL_FUND_ID:" + canonical)
        seen.add(canonical)

        rows.append(
            ErsteHungaryEvidenceSurfaceRow(
                as_of=str(raw["as_of"]),
                canonical_fund_id=canonical,
                isin=(str(raw["isin"]).strip() or None)
                if raw.get("isin") is not None else None,
                instrument_id=(str(raw["instrument_id"]).strip() or None)
                if raw.get("instrument_id") is not None else None,
                category_id=(str(raw["category_id"]).strip() or None)
                if raw.get("category_id") is not None else None,
                classification=str(raw["classification"]).strip(),
                eligibility_reason=str(raw["eligibility_reason"]),
                f1_state=_normalize_evidence_state(raw["f1_state"]),
                f2_state=_normalize_evidence_state(raw["f2_state"]),
                f3_state=_normalize_evidence_state(raw["f3_state"]),
                f4_state=_normalize_evidence_state(raw["f4_state"]),
                f4_latest_date=(str(raw["f4_latest_date"]).strip() or None)
                if raw.get("f4_latest_date") is not None else None,
                f4_previous_date=(str(raw["f4_previous_date"]).strip() or None)
                if raw.get("f4_previous_date") is not None else None,
            )
        )

    return tuple(
        sorted(rows, key=lambda row: (row.classification, row.canonical_fund_id))
    )


def erste_hungary_evidence_rows(
    rows: tuple[ErsteHungaryEvidenceSurfaceRow, ...],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Fon": row.canonical_fund_id,
            "ISIN": row.isin or "-",
            "Kategori": row.category_id or "UNMAPPED",
            "Sinif": row.classification,
            "F1": row.f1_state,
            "F2": row.f2_state,
            "F3": row.f3_state,
            "F4": row.f4_state,
            "F4 Son": row.f4_latest_date or "-",
            "F4 Once": row.f4_previous_date or "-",
            "F5": row.f5_state,
            "Yetki": row.automatic_trade_authority,
            "Forced Fill": "YES" if row.forced_fill else "NO",
            "Gerekce": row.eligibility_reason,
        }
        for row in rows
    )

