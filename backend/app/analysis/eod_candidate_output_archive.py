from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

DEFAULT_EOD_OUTPUT_PATH = Path("backend/data/eod_candidate_output.json")
ISTANBUL = ZoneInfo("Europe/Istanbul")


class EodCandidateOutputJsonStore:
    """Kanonik kapan???n 5 dakikal?k de?erlendirmesini ayr? ar?ivler."""

    def __init__(self, path: Path | str = DEFAULT_EOD_OUTPUT_PATH) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"records": []}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {"records": []}
        if not isinstance(value, dict) or not isinstance(value.get("records"), list):
            return {"records": []}
        return value

    def save_record(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = self.load()
        records = [
            item for item in payload["records"]
            if not (
                isinstance(item, dict)
                and item.get("run_date") == record.get("run_date")
                and item.get("phase") == record.get("phase")
            )
        ]
        records.append(record)
        payload["records"] = records
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
        return record

    def latest(self) -> dict[str, Any] | None:
        records = self.load()["records"]
        return records[-1] if records else None


def make_eod_output_record(
    *,
    now: datetime,
    candidate_symbols: tuple[str, ...],
    batch: Any | None = None,
    output: Any | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    observed_at = now
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=ISTANBUL)
    else:
        observed_at = observed_at.astimezone(ISTANBUL)

    decisions: dict[str, Any] = {}
    if batch is not None:
        for symbol, decision in getattr(batch, "eod_decisions", {}).items():
            state = getattr(decision, "state", None)
            decisions[symbol] = {
                "state": getattr(state, "value", str(state)) if state is not None else None,
                "reason": str(getattr(decision, "reason", "")),
            }

    failures = []
    if batch is not None:
        failures = [
            {"symbol": item.symbol, "error": item.error}
            for item in getattr(batch, "failures", ())
        ]

    selected = tuple(getattr(output, "symbols", ())) if output is not None else ()
    return {
        "phase": "CANONICAL_CLOSE",
        "run_date": observed_at.date().isoformat(),
        "created_at": observed_at.isoformat(),
        "status": (
            "ERROR" if error else
            "NO_CANDIDATES" if not candidate_symbols else
            "SUCCESS" if batch is not None else
            "ERROR"
        ),
        "candidate_symbols": list(candidate_symbols),
        "candidate_count": len(candidate_symbols),
        "decisions": decisions,
        "buy_candidate_symbols": list(selected),
        "buy_candidate_count": len(selected),
        "failures": failures,
        "error": error,
    }
