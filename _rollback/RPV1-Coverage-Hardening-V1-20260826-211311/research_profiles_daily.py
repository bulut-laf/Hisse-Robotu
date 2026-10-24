from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from io import StringIO
import csv
import json
from typing import Iterable, Mapping

from .research_profiles import (
    CapexEvidence,
    CapexEvidenceStatus,
    CapexStage,
    FundamentalSnapshot,
    ProfileState,
    ResearchProfileResult,
    evaluate_research_profiles,
)


@dataclass(frozen=True)
class ResearchProfileContext:
    market_cap_try: float | None = None
    free_float_shares: float | None = None
    ttm_cfo: float | None = None
    ttm_operating_profit: float | None = None
    net_cash: float | None = None
    net_debt_ebitda: float | None = None
    debt_equity: float | None = None
    cfo_direction: str | None = None
    leverage_direction: str | None = None
    capex: CapexEvidence | None = None


@dataclass(frozen=True)
class DailyResearchProfileItem:
    symbol: str
    snapshot: FundamentalSnapshot
    results: tuple[ResearchProfileResult, ...]
    has_fundamental_periods: bool
    has_context: bool


@dataclass(frozen=True)
class DailyResearchProfileBundle:
    as_of: date
    successful_symbol_count: int
    covered_symbol_count: int
    items: tuple[DailyResearchProfileItem, ...]

    @property
    def results(self) -> tuple[ResearchProfileResult, ...]:
        return tuple(result for item in self.items for result in item.results)

    def state_count(self, state: ProfileState) -> int:
        return sum(result.state is state for result in self.results)


def _symbol(value: object) -> str:
    raw = str(value or "").strip().upper()
    if raw.endswith(".E"):
        raw = raw[:-2] + ".IS"
    if raw and "." not in raw:
        raw += ".IS"
    return raw


def _field(obj: object, *names: str) -> object | None:
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        lowered = {str(k).strip().lower(): v for k, v in obj.items()}
        for name in names:
            if name in obj:
                return obj[name]
            hit = lowered.get(name.lower())
            if hit is not None:
                return hit
        return None
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    return None


def _float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip().replace("₺", "").replace("TRY", "").replace(" ", "")
    if not raw:
        return None
    if raw.count(",") == 1 and raw.count(".") == 0:
        raw = raw.replace(",", ".")
    elif raw.count(",") >= 1 and raw.count(".") == 1 and raw.rfind(",") < raw.rfind("."):
        raw = raw.replace(",", "")
    elif raw.count(".") >= 1 and raw.count(",") == 1 and raw.rfind(".") < raw.rfind(","):
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    for parser in (
        date.fromisoformat,
        lambda x: datetime.strptime(x, "%d/%m/%Y").date(),
        lambda x: datetime.strptime(x, "%d.%m.%Y").date(),
    ):
        try:
            return parser(raw)
        except (ValueError, TypeError):
            continue
    return None


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {
        "1", "true", "yes", "evet", "e", "y", "var",
    }


_PERIOD_DATE_FIELDS = (
    "period_end", "period_end_date", "end_date", "period_date",
    "report_date", "date", "donem_sonu", "dönem_sonu",
)
_REVENUE_FIELDS = ("revenue", "sales", "hasilat", "hasılat")
_GROSS_PROFIT_FIELDS = ("gross_profit", "brut_kar", "brüt_kar")
_EBITDA_FIELDS = ("ebitda", "favok", "favök")
_OPERATING_PROFIT_FIELDS = (
    "operating_profit", "operating_income", "esas_faaliyet_kari",
    "esas_faaliyet_karı",
)
_CFO_FIELDS = (
    "operating_cash_flow", "cash_flow_from_operations",
    "faaliyet_nakit_akisi", "faaliyet_nakit_akışı",
)
_CASH_FIELDS = (
    "cash_and_equivalents", "cash", "nakit", "cash_equivalents",
)
_DEBT_FIELDS = (
    "total_debt", "financial_debt", "debt", "finansal_borc", "finansal_borç",
)


def _period_date(period: object) -> date | None:
    return _date(_field(period, *_PERIOD_DATE_FIELDS))


def _same_period_last_year(periods: list[object], latest_date: date) -> object | None:
    candidates: list[tuple[int, object]] = []
    for item in periods:
        item_date = _period_date(item)
        if item_date is None or item_date >= latest_date:
            continue
        delta = (latest_date - item_date).days
        if 320 <= delta <= 410:
            candidates.append((abs(delta - 365), item))
    return min(candidates, key=lambda x: x[0])[1] if candidates else None


def _pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1.0) * 100.0


def _margin(value: float | None, revenue: float | None) -> float | None:
    if value is None or revenue in (None, 0):
        return None
    return value / revenue * 100.0


def _delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return current - previous


def _trend(current: float | None, previous: float | None) -> str | None:
    if current is None or previous is None:
        return None
    tolerance = max(abs(previous) * 0.05, 1e-9)
    if current > previous + tolerance:
        return "improving"
    if current < previous - tolerance:
        return "deteriorating"
    return "stable"


def snapshot_from_periods(
    symbol: str,
    periods: Iterable[object],
    *,
    context: ResearchProfileContext | None = None,
) -> FundamentalSnapshot:
    context = context or ResearchProfileContext()
    ordered = sorted(
        tuple(periods),
        key=lambda item: _period_date(item) or date.min,
    )
    if not ordered:
        return FundamentalSnapshot(
            symbol=_symbol(symbol),
            market_cap_try=context.market_cap_try,
            free_float_shares=context.free_float_shares,
            ttm_cfo=context.ttm_cfo,
            ttm_operating_profit=context.ttm_operating_profit,
            net_cash=context.net_cash,
            net_debt_ebitda=context.net_debt_ebitda,
            debt_equity=context.debt_equity,
            cfo_direction=context.cfo_direction,
            leverage_direction=context.leverage_direction,
            capex=context.capex,
        )

    latest = ordered[-1]
    latest_date = _period_date(latest)
    previous = (
        _same_period_last_year(ordered, latest_date)
        if latest_date is not None
        else None
    )

    revenue = _float(_field(latest, *_REVENUE_FIELDS))
    previous_revenue = _float(_field(previous, *_REVENUE_FIELDS))

    gross_profit = _float(_field(latest, *_GROSS_PROFIT_FIELDS))
    previous_gross_profit = _float(_field(previous, *_GROSS_PROFIT_FIELDS))

    ebitda = _float(_field(latest, *_EBITDA_FIELDS))
    previous_ebitda = _float(_field(previous, *_EBITDA_FIELDS))

    operating_profit = _float(_field(latest, *_OPERATING_PROFIT_FIELDS))
    previous_operating_profit = _float(
        _field(previous, *_OPERATING_PROFIT_FIELDS)
    )

    current_cfo = _float(_field(latest, *_CFO_FIELDS))
    previous_cfo = _float(_field(previous, *_CFO_FIELDS))

    cash = _float(_field(latest, *_CASH_FIELDS))
    debt = _float(_field(latest, *_DEBT_FIELDS))
    previous_cash = _float(_field(previous, *_CASH_FIELDS))
    previous_debt = _float(_field(previous, *_DEBT_FIELDS))

    computed_net_cash = (
        cash - debt if cash is not None and debt is not None else None
    )
    previous_net_cash = (
        previous_cash - previous_debt
        if previous_cash is not None and previous_debt is not None
        else None
    )

    explicit_ttm_cfo = _float(
        _field(latest, "ttm_cfo", "ttm_operating_cash_flow")
    )
    explicit_ttm_operating_profit = _float(
        _field(latest, "ttm_operating_profit", "ttm_operating_income")
    )

    cfo_direction = context.cfo_direction or _trend(current_cfo, previous_cfo)
    leverage_direction = context.leverage_direction or _trend(
        computed_net_cash, previous_net_cash
    )

    return FundamentalSnapshot(
        symbol=_symbol(symbol),
        market_cap_try=context.market_cap_try,
        free_float_shares=context.free_float_shares,
        ttm_cfo=(
            context.ttm_cfo
            if context.ttm_cfo is not None
            else explicit_ttm_cfo
        ),
        ttm_operating_profit=(
            context.ttm_operating_profit
            if context.ttm_operating_profit is not None
            else explicit_ttm_operating_profit
        ),
        latest_ebitda=ebitda,
        latest_operating_profit=operating_profit,
        net_cash=(
            context.net_cash
            if context.net_cash is not None
            else computed_net_cash
        ),
        net_debt_ebitda=context.net_debt_ebitda,
        debt_equity=context.debt_equity,
        revenue_yoy_pct=_pct_change(revenue, previous_revenue),
        gross_margin_delta_pp=_delta(
            _margin(gross_profit, revenue),
            _margin(previous_gross_profit, previous_revenue),
        ),
        ebitda_margin_delta_pp=_delta(
            _margin(ebitda, revenue),
            _margin(previous_ebitda, previous_revenue),
        ),
        operating_profit_yoy_pct=_pct_change(
            operating_profit, previous_operating_profit
        ),
        cfo_direction=cfo_direction,
        leverage_direction=leverage_direction,
        capex=context.capex,
    )


def _group_periods(periods: Iterable[object]) -> dict[str, list[object]]:
    grouped: dict[str, list[object]] = {}
    for period in periods:
        symbol = _symbol(_field(period, "symbol", "sembol"))
        if symbol:
            grouped.setdefault(symbol, []).append(period)
    return grouped


def build_daily_research_profiles(
    *,
    successful_symbols: Iterable[str],
    periods: Iterable[object] = (),
    contexts: Mapping[str, ResearchProfileContext] | None = None,
    as_of: date,
) -> DailyResearchProfileBundle:
    normalized_symbols = tuple(
        dict.fromkeys(_symbol(symbol) for symbol in successful_symbols if _symbol(symbol))
    )
    grouped = _group_periods(periods)
    normalized_contexts = {
        _symbol(symbol): context for symbol, context in (contexts or {}).items()
    }

    items: list[DailyResearchProfileItem] = []
    covered = 0
    for symbol in normalized_symbols:
        symbol_periods = tuple(grouped.get(symbol, ()))
        context = normalized_contexts.get(symbol)
        has_context = context is not None
        if symbol_periods or has_context:
            covered += 1
        snapshot = snapshot_from_periods(
            symbol,
            symbol_periods,
            context=context,
        )
        items.append(
            DailyResearchProfileItem(
                symbol=symbol,
                snapshot=snapshot,
                results=evaluate_research_profiles(snapshot, as_of=as_of),
                has_fundamental_periods=bool(symbol_periods),
                has_context=has_context,
            )
        )

    return DailyResearchProfileBundle(
        as_of=as_of,
        successful_symbol_count=len(normalized_symbols),
        covered_symbol_count=covered,
        items=tuple(items),
    )


def build_daily_research_profiles_from_snapshots(
    snapshots: Mapping[str, FundamentalSnapshot],
    *,
    as_of: date,
) -> DailyResearchProfileBundle:
    items = []
    for symbol, snapshot in snapshots.items():
        normalized = _symbol(symbol)
        effective = snapshot if snapshot.symbol == normalized else replace(
            snapshot, symbol=normalized
        )
        items.append(
            DailyResearchProfileItem(
                symbol=normalized,
                snapshot=effective,
                results=evaluate_research_profiles(effective, as_of=as_of),
                has_fundamental_periods=True,
                has_context=True,
            )
        )
    return DailyResearchProfileBundle(
        as_of=as_of,
        successful_symbol_count=len(items),
        covered_symbol_count=len(items),
        items=tuple(items),
    )


def research_profile_as_of_from_scan(
    scan_result: object,
    *,
    fallback: date | None = None,
) -> date:
    dates: list[date] = []
    for item in tuple(getattr(scan_result, "tum_sonuclar", ()) or ()):
        value = _date(getattr(item, "analiz_tarihi", None))
        if value is not None:
            dates.append(value)
    return max(dates) if dates else (fallback or date.today())


def daily_research_profile_rows(
    bundle: DailyResearchProfileBundle,
) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for item in bundle.items:
        snapshot = item.snapshot
        for result in item.results:
            rows.append(
                {
                    "Hisse": item.symbol.removesuffix(".IS"),
                    "Profil": result.profile.value,
                    "Durum": result.state.value,
                    "Fundamental yön": result.direction.value,
                    "Piyasa değeri": snapshot.market_cap_try,
                    "Fiili dolaşım lot": snapshot.free_float_shares,
                    "Net nakit": snapshot.net_cash,
                    "Ciro YoY (%)": snapshot.revenue_yoy_pct,
                    "Brüt marj Δ (pp)": snapshot.gross_margin_delta_pp,
                    "FAVÖK marj Δ (pp)": snapshot.ebitda_margin_delta_pp,
                    "Capex aşaması": (
                        snapshot.capex.stage.value
                        if snapshot.capex is not None
                        else None
                    ),
                    "Neden": " | ".join(result.reasons),
                    "İzleme": " | ".join(result.warnings),
                }
            )
    return tuple(rows)


def daily_research_profile_summary(
    bundle: DailyResearchProfileBundle,
) -> dict[str, int]:
    return {
        state.value: bundle.state_count(state)
        for state in ProfileState
    }


def _first(record: Mapping[str, object], *keys: str) -> object | None:
    lowered = {str(k).strip().lower(): v for k, v in record.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def _capex_from_record(record: Mapping[str, object]) -> CapexEvidence | None:
    stage_raw = _first(record, "capex_stage", "yatirim_asamasi", "yatırım_aşaması")
    status_raw = _first(
        record, "capex_evidence_status", "capex_status", "yatirim_kanit_durumu"
    )
    source_date = _date(_first(record, "capex_source_date", "yatirim_kaynak_tarihi"))
    source_id = _first(record, "capex_source_id", "kap_bildirim_id", "yatirim_kaynak_id")
    if not stage_raw or not status_raw or source_date is None or not source_id:
        return None
    try:
        stage = CapexStage(str(stage_raw).strip().upper())
        status = CapexEvidenceStatus(str(status_raw).strip().upper())
    except ValueError:
        return None
    return CapexEvidence(
        source_type=str(
            _first(record, "capex_source_type", "yatirim_kaynak_turu") or "MANUAL"
        ),
        source_date=source_date,
        source_id=str(source_id),
        investment_type=str(
            _first(record, "capex_investment_type", "yatirim_turu") or "capacity"
        ),
        stage=stage,
        evidence_status=status,
        expected_completion_date=_date(
            _first(record, "capex_expected_completion_date", "yatirim_tamamlanma_tarihi")
        ),
        commissioned_date=_date(
            _first(record, "capex_commissioned_date", "devreye_alma_tarihi")
        ),
        investment_amount=_float(
            _first(record, "capex_investment_amount", "yatirim_tutari")
        ),
        currency=(
            str(_first(record, "capex_currency", "yatirim_para_birimi"))
            if _first(record, "capex_currency", "yatirim_para_birimi")
            else None
        ),
        capacity_before=_float(
            _first(record, "capacity_before", "kapasite_once")
        ),
        capacity_after=_float(
            _first(record, "capacity_after", "kapasite_sonra")
        ),
        expected_revenue_impact=_float(
            _first(record, "expected_revenue_impact", "beklenen_ciro_katkisi")
        ),
        expected_margin_impact=_float(
            _first(record, "expected_margin_impact", "beklenen_marj_katkisi")
        ),
        expected_cost_impact=_float(
            _first(record, "expected_cost_impact", "beklenen_maliyet_etkisi")
        ),
        new_product=_bool(_first(record, "capex_new_product", "yeni_urun")),
        new_geography=_bool(_first(record, "capex_new_geography", "yeni_cografya")),
        new_customer_segment=_bool(
            _first(record, "capex_new_customer_segment", "yeni_musteri_segmenti")
        ),
    )


def _context_from_record(record: Mapping[str, object]) -> tuple[str, ResearchProfileContext] | None:
    symbol = _symbol(_first(record, "symbol", "sembol", "hisse"))
    if not symbol:
        return None
    return symbol, ResearchProfileContext(
        market_cap_try=_float(
            _first(record, "market_cap_try", "market_cap", "piyasa_degeri")
        ),
        free_float_shares=_float(
            _first(record, "free_float_shares", "free_float_lot", "fiili_dolasim_lot")
        ),
        ttm_cfo=_float(_first(record, "ttm_cfo", "ttm_operating_cash_flow")),
        ttm_operating_profit=_float(
            _first(record, "ttm_operating_profit", "ttm_operating_income")
        ),
        net_cash=_float(_first(record, "net_cash", "net_nakit")),
        net_debt_ebitda=_float(
            _first(record, "net_debt_ebitda", "net_borc_favok")
        ),
        debt_equity=_float(_first(record, "debt_equity", "borc_ozkaynak")),
        cfo_direction=(
            str(_first(record, "cfo_direction", "cfo_yonu"))
            if _first(record, "cfo_direction", "cfo_yonu")
            else None
        ),
        leverage_direction=(
            str(_first(record, "leverage_direction", "borcluluk_yonu"))
            if _first(record, "leverage_direction", "borcluluk_yonu")
            else None
        ),
        capex=_capex_from_record(record),
    )


def research_profile_contexts_from_bytes(
    data: bytes,
    *,
    suffix: str,
) -> dict[str, ResearchProfileContext]:
    suffix = suffix.lower().strip()
    records: list[Mapping[str, object]]
    if suffix == ".csv":
        text = data.decode("utf-8-sig")
        records = list(csv.DictReader(StringIO(text)))
    elif suffix == ".json":
        payload = json.loads(data.decode("utf-8-sig"))
        if isinstance(payload, list):
            records = [item for item in payload if isinstance(item, Mapping)]
        elif isinstance(payload, Mapping):
            source = payload.get("periods", payload.get("records", payload))
            if isinstance(source, list):
                records = [item for item in source if isinstance(item, Mapping)]
            else:
                records = [payload]
        else:
            records = []
    else:
        return {}

    out: dict[str, ResearchProfileContext] = {}
    for record in records:
        parsed = _context_from_record(record)
        if parsed is None:
            continue
        symbol, context = parsed
        previous = out.get(symbol)
        if previous is None:
            out[symbol] = context
            continue
        out[symbol] = ResearchProfileContext(
            market_cap_try=context.market_cap_try or previous.market_cap_try,
            free_float_shares=context.free_float_shares or previous.free_float_shares,
            ttm_cfo=context.ttm_cfo if context.ttm_cfo is not None else previous.ttm_cfo,
            ttm_operating_profit=(
                context.ttm_operating_profit
                if context.ttm_operating_profit is not None
                else previous.ttm_operating_profit
            ),
            net_cash=context.net_cash if context.net_cash is not None else previous.net_cash,
            net_debt_ebitda=(
                context.net_debt_ebitda
                if context.net_debt_ebitda is not None
                else previous.net_debt_ebitda
            ),
            debt_equity=(
                context.debt_equity
                if context.debt_equity is not None
                else previous.debt_equity
            ),
            cfo_direction=context.cfo_direction or previous.cfo_direction,
            leverage_direction=context.leverage_direction or previous.leverage_direction,
            capex=context.capex or previous.capex,
        )
    return out
