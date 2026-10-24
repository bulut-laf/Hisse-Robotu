from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable


CATEGORY_VERSION = "erste-hungary-category-normalization-v1"
RANK_SEED_VERSION = "erste-hungary-rank-seed-v1"


def _ascii_fold(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(
        ch for ch in normalized
        if not unicodedata.combining(ch)
    ).casefold().strip()


def normalize_category(raw: str | None) -> str | None:
    text = _ascii_fold(raw)
    if not text:
        return None

    compact = re.sub(r"\s+", " ", text)

    rules = (
        ("EQUITY", ("reszveny", "equity", "stock")),
        ("BOND", ("kotveny", "bond", "fixed income")),
        ("MONEY_MARKET", ("penzpiac", "penzpiaci", "money market")),
        ("MIXED", ("vegyes", "mixed", "balanced")),
        ("ABSOLUTE_RETURN", ("abszolut hozamu", "abszolut", "absolute return")),
        ("REAL_ESTATE", ("ingatlan", "real estate")),
        ("COMMODITY", ("nyersanyag", "arupiaci", "commodity")),
        ("FUND_OF_FUNDS", ("alapok alapja", "fund of funds")),
        ("DERIVATIVE", ("szarmaztatott", "derivative")),
        ("GUARANTEED_OR_PROTECTED", ("garantalt", "tokegarantalt", "vedett")),
    )

    for normalized, needles in rules:
        if any(needle in compact for needle in needles):
            return normalized

    return f"OTHER::{compact.upper()}"


def _decimal(value: Any) -> Decimal | None:
    if value in (None, "", "-"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class RankSeedRow:
    isin: str
    category_raw: str | None
    category_normalized: str | None
    return_ytd: Decimal | None
    return_1y: Decimal | None
    return_5y: Decimal | None
    volatility_1y: Decimal | None
    max_drawdown_1y: Decimal | None
    rank_score: Decimal | None
    rank_position: int | None
    category_size: int
    rank_percentile: Decimal | None


def _score_record(record: dict[str, Any]) -> Decimal | None:
    values = {
        "ytd": _decimal(record.get("return_ytd")),
        "r1y": _decimal(record.get("return_1y")),
        "r5y": _decimal(record.get("return_5y")),
        "vol1y": _decimal(record.get("volatility_1y")),
        "dd1y": _decimal(record.get("max_drawdown_1y")),
    }

    return_parts: list[Decimal] = []
    weights: list[Decimal] = []

    if values["ytd"] is not None:
        return_parts.append(values["ytd"] * Decimal("0.20"))
        weights.append(Decimal("0.20"))
    if values["r1y"] is not None:
        return_parts.append(values["r1y"] * Decimal("0.50"))
        weights.append(Decimal("0.50"))
    if values["r5y"] is not None:
        return_parts.append(values["r5y"] * Decimal("0.30"))
        weights.append(Decimal("0.30"))

    if not return_parts:
        return None

    return_score = sum(return_parts) / sum(weights)

    risk_penalty = Decimal("0")
    if values["vol1y"] is not None:
        risk_penalty += values["vol1y"] * Decimal("0.20")
    if values["dd1y"] is not None:
        risk_penalty += abs(values["dd1y"]) * Decimal("0.20")

    return return_score - risk_penalty


def build_rank_seed(records: Iterable[dict[str, Any]]) -> list[RankSeedRow]:
    prepared: list[dict[str, Any]] = []

    for record in records:
        isin = str(record.get("isin") or "").strip().upper()
        if not isin:
            continue

        category_raw = record.get("category_raw")
        category_normalized = normalize_category(category_raw)

        prepared.append(
            {
                "isin": isin,
                "category_raw": category_raw,
                "category_normalized": category_normalized,
                "return_ytd": _decimal(record.get("return_ytd")),
                "return_1y": _decimal(record.get("return_1y")),
                "return_5y": _decimal(record.get("return_5y")),
                "volatility_1y": _decimal(record.get("volatility_1y")),
                "max_drawdown_1y": _decimal(record.get("max_drawdown_1y")),
                "score": _score_record(record),
            }
        )

    by_category: dict[str, list[dict[str, Any]]] = {}
    for item in prepared:
        category = item["category_normalized"]
        if not category:
            continue
        by_category.setdefault(category, []).append(item)

    rank_info: dict[str, tuple[int | None, int, Decimal | None]] = {}

    for category, items in by_category.items():
        ranked = sorted(
            items,
            key=lambda item: (
                item["score"] is None,
                -(item["score"] or Decimal("0")),
                item["isin"],
            ),
        )

        category_size = len(ranked)
        numeric_rank = 0
        for item in ranked:
            if item["score"] is None:
                rank_info[item["isin"]] = (None, category_size, None)
                continue

            numeric_rank += 1
            if category_size <= 1:
                percentile = Decimal("1")
            else:
                percentile = (
                    Decimal(category_size - numeric_rank)
                    / Decimal(category_size - 1)
                )

            rank_info[item["isin"]] = (
                numeric_rank,
                category_size,
                percentile,
            )

    rows: list[RankSeedRow] = []
    for item in sorted(prepared, key=lambda x: x["isin"]):
        rank_position, category_size, percentile = rank_info.get(
            item["isin"],
            (None, 0, None),
        )

        rows.append(
            RankSeedRow(
                isin=item["isin"],
                category_raw=item["category_raw"],
                category_normalized=item["category_normalized"],
                return_ytd=item["return_ytd"],
                return_1y=item["return_1y"],
                return_5y=item["return_5y"],
                volatility_1y=item["volatility_1y"],
                max_drawdown_1y=item["max_drawdown_1y"],
                rank_score=item["score"],
                rank_position=rank_position,
                category_size=category_size,
                rank_percentile=percentile,
            )
        )

    return rows


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records