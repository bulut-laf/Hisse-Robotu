from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


CONTRACT_VERSION = "erste-shadow-portfolio-v1"
PORTFOLIO_ID = "erste-shadow-portfolio-v1"


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_{field.upper()}") from exc
    if not result.is_finite():
        raise ValueError(f"INVALID_{field.upper()}")
    return result


def _date(value: Any, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_{field.upper()}") from exc


def _normalize_isin(value: Any) -> str:
    isin = str(value or "").strip().upper().replace(" ", "")
    if len(isin) != 12 or not isin[:2].isalpha() or not isin[-1:].isdigit():
        raise ValueError(f"INVALID_ISIN:{isin or 'EMPTY'}")
    if not isin.isalnum():
        raise ValueError(f"INVALID_ISIN:{isin}")
    return isin


@dataclass(frozen=True, slots=True)
class FundShadowPosition:
    canonical_fund_id: str
    isin: str
    name: str
    currency: str
    initial_nav: str
    initial_nav_date: str
    units: str
    initial_value_local: str
    weight: str
    latest_nav: str
    latest_nav_date: str
    source_url: str
    source_date: str | None
    erste_access_status: str
    sale_eligibility_confirmed: bool
    currency_return_pct: str
    data_status: str = "INITIALIZED"


@dataclass(frozen=True, slots=True)
class FundShadowPortfolio:
    portfolio_id: str
    contract_version: str
    created_at: str
    updated_at: str
    positions: tuple[FundShadowPosition, ...]
    currency_policy: str = "SEPARATE_CURRENCY_BUCKETS_NO_FX_CONVERSION"
    execution_authority: str = "NONE"


class ErsteShadowPortfolioStore:
    """Separate persistence for Erste fund shadow positions; never touches stock portfolio storage."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else (
            Path.home() / ".hisse_robotu" / "erste_golge_portfoy_v1.json"
        )

    def load(self) -> FundShadowPortfolio:
        if not self.path.exists():
            now = datetime.now(timezone.utc).isoformat()
            return FundShadowPortfolio(
                portfolio_id=PORTFOLIO_ID,
                contract_version=CONTRACT_VERSION,
                created_at=now,
                updated_at=now,
                positions=(),
            )
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            positions = tuple(FundShadowPosition(**row) for row in payload.get("positions", []))
            return FundShadowPortfolio(
                portfolio_id=payload["portfolio_id"],
                contract_version=payload["contract_version"],
                created_at=payload["created_at"],
                updated_at=payload["updated_at"],
                positions=positions,
                currency_policy=payload.get(
                    "currency_policy", "SEPARATE_CURRENCY_BUCKETS_NO_FX_CONVERSION"
                ),
                execution_authority=payload.get("execution_authority", "NONE"),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"INVALID_ERSTE_SHADOW_PORTFOLIO_FILE:{self.path}") from exc

    def save(self, portfolio: FundShadowPortfolio) -> None:
        if portfolio.execution_authority != "NONE":
            raise ValueError("EXECUTION_AUTHORITY_MUST_REMAIN_NONE")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "portfolio_id": portfolio.portfolio_id,
            "contract_version": portfolio.contract_version,
            "created_at": portfolio.created_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "currency_policy": portfolio.currency_policy,
            "execution_authority": "NONE",
            "positions": [asdict(position) for position in portfolio.positions],
        }
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def add_verified_funds(
        self,
        snapshots: Iterable[Any],
        *,
        sale_eligible_isins: set[str],
        initial_value_per_fund: Decimal | int | str = "100",
    ) -> FundShadowPortfolio:
        """Add only explicitly confirmed sale-eligible funds with dated positive NAV.

        Each fund is initialized to a normalized local-currency value (default 100).
        Different currencies remain separate; no FX conversion or combined monetary
        total is calculated. This is a performance index, not an order or recommendation.
        """
        initial_value = _decimal(initial_value_per_fund, "initial_value_per_fund")
        if initial_value <= 0:
            raise ValueError("INITIAL_VALUE_MUST_BE_POSITIVE")
        eligible = {_normalize_isin(value) for value in sale_eligible_isins}
        current = self.load()
        by_isin = {position.isin: position for position in current.positions}
        candidate_rows: dict[str, Any] = {}
        for snapshot in snapshots:
            isin = _normalize_isin(getattr(snapshot, "isin", ""))
            if isin in eligible:
                candidate_rows[isin] = snapshot

        missing = sorted(eligible - set(candidate_rows))
        if missing:
            raise ValueError("ELIGIBLE_FUND_SNAPSHOT_MISSING:" + ",".join(missing))

        new_positions: list[FundShadowPosition] = []
        for isin in sorted(eligible):
            snapshot = candidate_rows[isin]
            nav = _decimal(getattr(snapshot, "nav", None), "nav")
            if nav <= 0:
                raise ValueError(f"NON_POSITIVE_NAV:{isin}")
            nav_date = getattr(snapshot, "nav_date", None)
            if nav_date is None:
                raise ValueError(f"NAV_DATE_MISSING:{isin}")
            nav_date = _date(nav_date, "nav_date")
            currency = str(getattr(snapshot, "currency", None) or "").strip().upper()
            if not currency:
                raise ValueError(f"CURRENCY_MISSING:{isin}")
            source_url = str(getattr(snapshot, "source_url", "") or "").strip()
            if not source_url:
                raise ValueError(f"SOURCE_URL_MISSING:{isin}")
            source_date_value = getattr(snapshot, "source_date", None)
            source_date = _date(source_date_value, "source_date").isoformat() if source_date_value else None
            canonical_id = str(
                getattr(snapshot, "canonical_fund_id", "") or f"fund:isin:{isin}"
            )
            name = str(getattr(snapshot, "name", "") or isin).strip()
            access_status = str(getattr(snapshot, "erste_access_status", None) or "UNVERIFIED")
            # Each fund receives its own normalized starting value in its local currency.
            units = initial_value / nav
            position = FundShadowPosition(
                canonical_fund_id=canonical_id,
                isin=isin,
                name=name,
                currency=currency,
                initial_nav=str(nav),
                initial_nav_date=nav_date.isoformat(),
                units=str(units),
                initial_value_local=str(initial_value),
                weight=str(Decimal("1") / Decimal(len(eligible))),
                latest_nav=str(nav),
                latest_nav_date=nav_date.isoformat(),
                source_url=source_url,
                source_date=source_date,
                erste_access_status=access_status,
                sale_eligibility_confirmed=True,
                currency_return_pct="0",
                data_status="INITIALIZED",
            )
            existing = by_isin.get(isin)
            if existing and existing.initial_nav != position.initial_nav:
                raise ValueError(f"FUND_ALREADY_INITIALIZED_WITH_DIFFERENT_NAV:{isin}")
            by_isin[isin] = existing or position

        # Recompute equal weights across the full current portfolio.
        positions = tuple(
            FundShadowPosition(**{
                **asdict(position),
                "weight": str(Decimal("1") / Decimal(len(by_isin))),
            })
            for _, position in sorted(by_isin.items())
        ) if by_isin else ()
        portfolio = FundShadowPortfolio(
            portfolio_id=PORTFOLIO_ID,
            contract_version=CONTRACT_VERSION,
            created_at=current.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            positions=positions,
        )
        self.save(portfolio)
        return self.load()

    def update_nav(self, isin: str, nav: Decimal | int | str, nav_date: date | str,
                   *, source_url: str, source_date: date | str | None = None) -> FundShadowPortfolio:
        normalized_isin = _normalize_isin(isin)
        current = self.load()
        latest_nav = _decimal(nav, "nav")
        if latest_nav <= 0:
            raise ValueError("NAV_MUST_BE_POSITIVE")
        effective_date = _date(nav_date, "nav_date")
        source = str(source_url or "").strip()
        if not source:
            raise ValueError("SOURCE_URL_MISSING")
        found = False
        updated: list[FundShadowPosition] = []
        for position in current.positions:
            if position.isin != normalized_isin:
                updated.append(position)
                continue
            found = True
            initial_nav = Decimal(position.initial_nav)
            return_pct = ((latest_nav / initial_nav) - Decimal("1")) * Decimal("100")
            updated.append(FundShadowPosition(**{
                **asdict(position),
                "latest_nav": str(latest_nav),
                "latest_nav_date": effective_date.isoformat(),
                "source_url": source,
                "source_date": _date(source_date, "source_date").isoformat() if source_date else None,
                "currency_return_pct": str(return_pct),
                "data_status": "UPDATED",
            }))
        if not found:
            raise ValueError(f"FUND_NOT_IN_SHADOW_PORTFOLIO:{normalized_isin}")
        result = FundShadowPortfolio(
            portfolio_id=current.portfolio_id,
            contract_version=current.contract_version,
            created_at=current.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            positions=tuple(updated),
            currency_policy=current.currency_policy,
            execution_authority="NONE",
        )
        self.save(result)
        return self.load()
