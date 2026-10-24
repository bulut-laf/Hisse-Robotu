from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Final, Mapping
from urllib.parse import unquote, urlparse

from app.analysis.financial_intelligence_bank_canonical_adapter import (
    adapt_bank_canonical_input,
)
from app.analysis.financial_intelligence_bank_scoring_engine import (
    score_bank_model,
)


BANK_PRODUCTION_SOURCE_ONBOARDING_VERSION: Final[str] = (
    "BANK_PRODUCTION_SOURCE_ONBOARDING_CONTRACT_V1"
)

OFFICIAL_SOURCE_BUNDLE_TYPE: Final[str] = (
    "OFFICIAL_SOURCE_BUNDLE"
)

OFFICIAL_SOURCE_BUNDLE_VERSION: Final[str] = (
    "BANK_OFFICIAL_EVIDENCE_BUNDLE_V1"
)

DISALLOWED_SOURCE_TYPES: Final[frozenset[str]] = frozenset({
    "SYNTHETIC",
    "CONTRACT",
    "TEST",
    "FIXTURE",
    "MOCK",
})

REQUIRED_TOP_LEVEL_FIELDS: Final[tuple[str, ...]] = (
    "source_type",
    "source_uri",
    "symbol",
    "sector_model",
    "as_of",
    "publication_date",
    "canonical_facts",
    "evidence_hash",
)

_SHA256_RE: Final[re.Pattern[str]] = re.compile(
    r"^sha256:[0-9a-fA-F]{64}$"
)


@dataclass(frozen=True)
class BankProductionSourceOnboardingResult:
    status: str
    symbol: str | None
    source_type: str | None
    source_uri: str | None
    as_of: str | None
    publication_date: str | None
    canonical_input_ready: bool
    scoring_ready: bool
    production_evidence: bool
    activation_ready: bool
    blocker: str | None


def _clean(value: object) -> str:
    return str(value or "").strip()


def _iso(value: object, field: str) -> str:
    text = _clean(value)

    if not text:
        raise ValueError(f"{field}_MISSING")

    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"{field}_INVALID:{text}"
        ) from exc

    return parsed.isoformat()


def _blocked(
    *,
    symbol: str | None,
    source_type: str | None,
    source_uri: str | None,
    blocker: str,
    as_of: str | None = None,
    publication_date: str | None = None,
    canonical_input_ready: bool = False,
) -> BankProductionSourceOnboardingResult:
    return BankProductionSourceOnboardingResult(
        status="BLOCKED",
        symbol=symbol,
        source_type=source_type,
        source_uri=source_uri,
        as_of=as_of,
        publication_date=publication_date,
        canonical_input_ready=canonical_input_ready,
        scoring_ready=False,
        production_evidence=False,
        activation_ready=False,
        blocker=blocker,
    )


def _file_uri_to_path(source_uri: str) -> Path | None:
    parsed = urlparse(source_uri)

    if parsed.scheme.casefold() != "file":
        return None

    raw_path = unquote(parsed.path)

    # file:///D:/... -> D:/... on Windows.
    if (
        len(raw_path) >= 3
        and raw_path.startswith("/")
        and raw_path[2] == ":"
    ):
        raw_path = raw_path[1:]

    if parsed.netloc:
        raw_path = (
            f"//{parsed.netloc}{raw_path}"
        )

    return Path(raw_path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _validate_official_source_bundle(
    record: Mapping[str, Any],
    *,
    source_uri: str,
    evidence_hash: str,
) -> str | None:
    if not _SHA256_RE.fullmatch(evidence_hash):
        return "OFFICIAL_SOURCE_BUNDLE_HASH_INVALID"

    bundle_path = _file_uri_to_path(
        source_uri
    )

    if bundle_path is None:
        return "OFFICIAL_SOURCE_BUNDLE_URI_NOT_FILE"

    if not bundle_path.is_file():
        return "OFFICIAL_SOURCE_BUNDLE_FILE_MISSING"

    actual_hash = (
        "sha256:" + _sha256_file(bundle_path)
    )

    if actual_hash.casefold() != evidence_hash.casefold():
        return "OFFICIAL_SOURCE_BUNDLE_HASH_MISMATCH"

    try:
        bundle_raw = bundle_path.read_text(
            encoding="utf-8-sig"
        )
        bundle = json.loads(bundle_raw)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "OFFICIAL_SOURCE_BUNDLE_INVALID_JSON"

    if not isinstance(bundle, Mapping):
        return "OFFICIAL_SOURCE_BUNDLE_INVALID"

    if (
        _clean(bundle.get("bundle_version"))
        != OFFICIAL_SOURCE_BUNDLE_VERSION
    ):
        return "OFFICIAL_SOURCE_BUNDLE_VERSION_INVALID"

    expected_metadata = {
        "symbol": _clean(
            record.get("symbol")
        ).upper(),
        "sector_model": _clean(
            record.get("sector_model")
        ).upper(),
        "period_end": _clean(
            record.get("period_end")
        ),
        "publication_date": _clean(
            record.get("publication_date")
        ),
        "as_of": _clean(
            record.get("as_of")
        ),
    }

    actual_metadata = {
        "symbol": _clean(
            bundle.get("symbol")
        ).upper(),
        "sector_model": _clean(
            bundle.get("sector_model")
        ).upper(),
        "period_end": _clean(
            bundle.get("period_end")
        ),
        "publication_date": _clean(
            bundle.get("publication_date")
        ),
        "as_of": _clean(
            bundle.get("as_of")
        ),
    }

    for field, expected in expected_metadata.items():
        if actual_metadata[field] != expected:
            return (
                "OFFICIAL_SOURCE_BUNDLE_METADATA_MISMATCH:"
                f"{field}"
            )

    record_facts = record.get(
        "canonical_facts"
    )
    bundle_facts = bundle.get(
        "canonical_facts"
    )

    if not isinstance(record_facts, Mapping):
        return (
            "OFFICIAL_SOURCE_BUNDLE_RECORD_FACTS_INVALID"
        )

    if not isinstance(bundle_facts, Mapping):
        return (
            "OFFICIAL_SOURCE_BUNDLE_FACTS_INVALID"
        )

    if dict(bundle_facts) != dict(record_facts):
        return (
            "OFFICIAL_SOURCE_BUNDLE_CANONICAL_FACTS_MISMATCH"
        )

    sources = bundle.get("sources")

    if not isinstance(sources, Mapping) or not sources:
        return "OFFICIAL_SOURCE_BUNDLE_SOURCES_INVALID"

    for source_id, source in sources.items():
        source_id_text = _clean(source_id)

        if not source_id_text:
            return (
                "OFFICIAL_SOURCE_BUNDLE_SOURCE_ID_INVALID"
            )

        if not isinstance(source, Mapping):
            return (
                "OFFICIAL_SOURCE_BUNDLE_SOURCE_INVALID:"
                f"{source_id_text}"
            )

        inner_type = _clean(
            source.get("source_type")
        ).upper()

        inner_uri = _clean(
            source.get("source_uri")
        )

        inner_hash = _clean(
            source.get("evidence_hash")
        )

        if not inner_type:
            return (
                "OFFICIAL_SOURCE_BUNDLE_SOURCE_TYPE_MISSING:"
                f"{source_id_text}"
            )

        if inner_type in DISALLOWED_SOURCE_TYPES:
            return (
                "OFFICIAL_SOURCE_BUNDLE_NON_PRODUCTION_SOURCE:"
                f"{source_id_text}:{inner_type}"
            )

        if not inner_uri:
            return (
                "OFFICIAL_SOURCE_BUNDLE_SOURCE_URI_MISSING:"
                f"{source_id_text}"
            )

        if not _SHA256_RE.fullmatch(inner_hash):
            return (
                "OFFICIAL_SOURCE_BUNDLE_SOURCE_HASH_INVALID:"
                f"{source_id_text}"
            )

    provenance = bundle.get(
        "metric_provenance"
    )

    if not isinstance(provenance, Mapping):
        return (
            "OFFICIAL_SOURCE_BUNDLE_PROVENANCE_INVALID"
        )

    fact_keys = {
        str(key)
        for key in bundle_facts
    }

    provenance_keys = {
        str(key)
        for key in provenance
    }

    if provenance_keys != fact_keys:
        return (
            "OFFICIAL_SOURCE_BUNDLE_PROVENANCE_COVERAGE_INVALID"
        )

    source_ids = {
        str(key)
        for key in sources
    }

    referenced_source_ids: set[str] = set()

    for metric in sorted(provenance_keys):
        source_id = _clean(
            provenance.get(metric)
        )

        if not source_id:
            return (
                "OFFICIAL_SOURCE_BUNDLE_PROVENANCE_SOURCE_MISSING:"
                f"{metric}"
            )

        if source_id not in source_ids:
            return (
                "OFFICIAL_SOURCE_BUNDLE_PROVENANCE_SOURCE_UNKNOWN:"
                f"{metric}:{source_id}"
            )

        referenced_source_ids.add(
            source_id
        )

    if referenced_source_ids != source_ids:
        return (
            "OFFICIAL_SOURCE_BUNDLE_UNUSED_SOURCE"
        )

    return None


def evaluate_bank_production_source(
    record: Mapping[str, Any],
) -> BankProductionSourceOnboardingResult:

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in record:
            return _blocked(
                symbol=None,
                source_type=None,
                source_uri=None,
                blocker=(
                    f"REQUIRED_FIELD_MISSING:{field}"
                ),
            )

    source_type = _clean(
        record.get("source_type")
    ).upper()

    source_uri = _clean(
        record.get("source_uri")
    )

    symbol = _clean(
        record.get("symbol")
    ).upper()

    evidence_hash = _clean(
        record.get("evidence_hash")
    )

    if source_type in DISALLOWED_SOURCE_TYPES:
        return _blocked(
            symbol=symbol or None,
            source_type=source_type or None,
            source_uri=source_uri or None,
            blocker=(
                f"NON_PRODUCTION_SOURCE_TYPE:{source_type}"
            ),
        )

    if not source_type:
        return _blocked(
            symbol=symbol or None,
            source_type=None,
            source_uri=source_uri or None,
            blocker="SOURCE_TYPE_MISSING",
        )

    if not source_uri:
        return _blocked(
            symbol=symbol or None,
            source_type=source_type,
            source_uri=None,
            blocker="SOURCE_URI_MISSING",
        )

    if not evidence_hash:
        return _blocked(
            symbol=symbol or None,
            source_type=source_type,
            source_uri=source_uri,
            blocker="EVIDENCE_HASH_MISSING",
        )

    if source_type == OFFICIAL_SOURCE_BUNDLE_TYPE:
        bundle_blocker = (
            _validate_official_source_bundle(
                record,
                source_uri=source_uri,
                evidence_hash=evidence_hash,
            )
        )

        if bundle_blocker is not None:
            return _blocked(
                symbol=symbol or None,
                source_type=source_type,
                source_uri=source_uri,
                blocker=bundle_blocker,
            )

    try:
        as_of = _iso(
            record.get("as_of"),
            "AS_OF",
        )

        publication_date = _iso(
            record.get("publication_date"),
            "PUBLICATION_DATE",
        )

    except ValueError as exc:
        return _blocked(
            symbol=symbol or None,
            source_type=source_type,
            source_uri=source_uri,
            blocker=str(exc),
        )

    canonical = adapt_bank_canonical_input(
        record
    )

    if canonical.status != "PASS":
        return _blocked(
            symbol=canonical.symbol,
            source_type=source_type,
            source_uri=source_uri,
            as_of=canonical.as_of or as_of,
            publication_date=(
                canonical.publication_date
                or publication_date
            ),
            blocker=str(
                canonical.blocker
            ),
        )

    if canonical.payload is None:
        return _blocked(
            symbol=canonical.symbol,
            source_type=source_type,
            source_uri=source_uri,
            as_of=canonical.as_of,
            publication_date=(
                canonical.publication_date
            ),
            blocker="BANK_CANONICAL_PAYLOAD_MISSING",
        )

    scored = score_bank_model(
        canonical.payload
    )

    if scored.status != "PASS":
        return _blocked(
            symbol=canonical.symbol,
            source_type=source_type,
            source_uri=source_uri,
            as_of=canonical.as_of,
            publication_date=(
                canonical.publication_date
            ),
            canonical_input_ready=True,
            blocker=str(
                scored.blocker
            ),
        )

    return BankProductionSourceOnboardingResult(
        status="PASS",
        symbol=canonical.symbol,
        source_type=source_type,
        source_uri=source_uri,
        as_of=canonical.as_of,
        publication_date=canonical.publication_date,
        canonical_input_ready=True,
        scoring_ready=True,
        production_evidence=True,
        activation_ready=True,
        blocker=None,
    )


__all__ = [
    "BANK_PRODUCTION_SOURCE_ONBOARDING_VERSION",
    "OFFICIAL_SOURCE_BUNDLE_TYPE",
    "OFFICIAL_SOURCE_BUNDLE_VERSION",
    "DISALLOWED_SOURCE_TYPES",
    "REQUIRED_TOP_LEVEL_FIELDS",
    "BankProductionSourceOnboardingResult",
    "evaluate_bank_production_source",
]
