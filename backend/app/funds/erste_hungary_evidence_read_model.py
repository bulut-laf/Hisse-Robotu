"""Read-only read model for the Erste Hungary F1-F4 evidence artifact.

This module does not calculate evidence, scores, classifications, trade decisions,
or fallback values. It only validates and exposes the already-produced artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


REQUIRED_FIELDS = (
    "canonical_fund_id",
    "category_id",
    "classification",
    "f1_state",
    "f2_state",
    "f3_state",
    "f4_state",
    "f4_latest_date",
    "f4_previous_date",
    "automatic_trade_authority",
    "forced_fill",
)


@dataclass(frozen=True)
class FundEvidenceSurfaceRow:
    canonical_fund_id: str
    category_id: str | None
    classification: str
    f1_state: str
    f2_state: str
    f3_state: str
    f4_state: str
    f4_latest_date: str | None
    f4_previous_date: str | None
    automatic_trade_authority: str
    forced_fill: bool

    @property
    def f5_state(self) -> str:
        # F5 is intentionally not synthesized into the artifact.
        return "SAFE_UNAVAILABLE"


class ErsteHungaryEvidenceReadModel:
    """Safe read-only adapter over the frozen F1-F4 artifact."""

    def __init__(self, artifact_path: str | Path):
        self.artifact_path = Path(artifact_path)

    def _payload(self) -> Any:
        with self.artifact_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def rows(self) -> list[FundEvidenceSurfaceRow]:
        payload = self._payload()
        if not isinstance(payload, list):
            raise ValueError("F1-F4 evidence artifact must be a JSON array")

        rows: list[FundEvidenceSurfaceRow] = []
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                raise ValueError(f"Evidence row {index} is not an object")

            missing = [key for key in REQUIRED_FIELDS if key not in item]
            if missing:
                raise ValueError(
                    f"Evidence row {index} missing required fields: {','.join(missing)}"
                )

            if item["automatic_trade_authority"] != "NONE":
                raise ValueError(
                    f"Evidence row {index} violates trade-authority invariant"
                )
            if item["forced_fill"] is not False:
                raise ValueError(
                    f"Evidence row {index} violates forced-fill invariant"
                )

            rows.append(
                FundEvidenceSurfaceRow(
                    canonical_fund_id=str(item["canonical_fund_id"]),
                    category_id=item["category_id"],
                    classification=str(item["classification"]),
                    f1_state=str(item["f1_state"]),
                    f2_state=str(item["f2_state"]),
                    f3_state=str(item["f3_state"]),
                    f4_state=str(item["f4_state"]),
                    f4_latest_date=item["f4_latest_date"],
                    f4_previous_date=item["f4_previous_date"],
                    automatic_trade_authority=str(item["automatic_trade_authority"]),
                    forced_fill=bool(item["forced_fill"]),
                )
            )
        return rows

    def by_fund(self, canonical_fund_id: str) -> FundEvidenceSurfaceRow | None:
        for row in self.rows():
            if row.canonical_fund_id == canonical_fund_id:
                return row
        return None