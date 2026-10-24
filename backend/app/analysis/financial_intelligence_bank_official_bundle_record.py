from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def build_bank_official_bundle_record(
    path: str | Path,
) -> dict[str, Any] | None:
    bundle_path = Path(path)

    if not bundle_path.exists():
        return None

    try:
        raw = bundle_path.read_bytes()
        bundle = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    required = (
        "symbol",
        "sector_model",
        "period_end",
        "publication_date",
        "as_of",
        "canonical_facts",
    )

    if any(key not in bundle for key in required):
        return None

    if not isinstance(bundle.get("canonical_facts"), dict):
        return None

    return {
        "source_type": "OFFICIAL_SOURCE_BUNDLE",
        "source_uri": bundle_path.resolve().as_uri(),
        "symbol": bundle["symbol"],
        "sector_model": bundle["sector_model"],
        "period_end": bundle["period_end"],
        "publication_date": bundle["publication_date"],
        "as_of": bundle["as_of"],
        "canonical_facts": bundle["canonical_facts"],
        "evidence_hash": (
            "sha256:" + hashlib.sha256(raw).hexdigest()
        ),
    }


__all__ = [
    "build_bank_official_bundle_record",
]