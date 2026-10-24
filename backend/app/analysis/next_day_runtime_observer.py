from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from backend.app.analysis.jump_candidate_entry_readiness import (
    evaluate_jump_candidate_entry_readiness,
)
from backend.app.analysis.next_day_observation_memory import persist_frozen_selection
from backend.app.analysis.next_day_selection import (
    ExtensionState,
    NextDayCandidateEvidence,
    ReboundState,
    select_next_day_candidates,
)
from backend.app.analysis.next_day_outcome_runtime_adapter import settle_pending_next_day_outcomes
from backend.app.analysis.weekly_opportunity_runtime import observe_weekly_opportunity_runtime
from backend.app.analysis.ranking_snapshot_adapter import persist_research_rank_snapshot

CONTRACT_ID = "NEXT_DAY_PHASE7C_RUNTIME_OBSERVER_V1"


class NextDayRuntimeObserverError(RuntimeError):
    pass


@dataclass(frozen=True)
class NextDayRuntimeObserverResult:
    canonical_date: str
    candidate_count: int
    primary_count: int
    reserve_count: int
    persistence_status: str


def _norm(value: object) -> str:
    text = str(value or "")
    table = str.maketrans({
        "İ": "I", "ı": "I", "Ş": "S", "ş": "S", "Ğ": "G", "ğ": "G",
        "Ü": "U", "ü": "U", "Ö": "O", "ö": "O", "Ç": "C", "ç": "C",
    })
    return " ".join(text.translate(table).upper().split())


def _sym(value: object) -> str:
    return str(value or "").strip().upper().removesuffix(".IS")


def _tuple(value: object) -> tuple[object, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    try:
        return tuple(value)
    except TypeError:
        return ()


def _canonical_date(scan_result: object, rows: tuple[object, ...]) -> str:
    raw = str(getattr(scan_result, "evren_tarihi", "") or "").strip()
    if len(raw) >= 10:
        try:
            return date.fromisoformat(raw[:10]).isoformat()
        except ValueError:
            pass

    found: set[str] = set()
    for item in rows:
        raw_date = str(getattr(item, "analiz_tarihi", "") or "")
        if len(raw_date) >= 10:
            try:
                found.add(date.fromisoformat(raw_date[:10]).isoformat())
            except ValueError:
                pass
    if len(found) == 1:
        return next(iter(found))
    raise NextDayRuntimeObserverError("CANONICAL_DATE_NOT_PROVEN")


def _visibility_index(contexts: Iterable[object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for item in contexts:
        symbol = _sym(getattr(item, "symbol", getattr(item, "sembol", "")))
        if symbol:
            out[symbol] = item
    return out


def _f1_positive(context: object | None) -> bool:
    if context is None:
        return False
    state = _norm(getattr(context, "visibility_state", getattr(context, "state", "")))
    if any(x in state for x in ("IMPROV", "GUCLEN", "IYILES")):
        return True
    try:
        return float(getattr(context, "rank_change")) > 0
    except (AttributeError, TypeError, ValueError):
        return False


def _reason_families(reasons: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    groups: dict[str, list[str]] = {"F2": [], "F3": [], "F5": []}
    for reason in reasons:
        n = _norm(reason)
        if any(x in n for x in ("TREND", "EMA", "YAPI", "STRUCTUR")):
            groups["F2"].append(reason)
        if any(x in n for x in ("MOMENTUM", "RSI", "MACD", "GORECELI GUC", "RELATIVE STRENGTH")):
            groups["F3"].append(reason)
        if any(x in n for x in ("HACIM", "VOLUME", "KATILIM")):
            groups["F5"].append(reason)
    return {k: tuple(dict.fromkeys(v)) for k, v in groups.items()}


def _readiness_positive(state: object) -> bool:
    n = _norm(state)
    if not any(x in n for x in ("HAZIR", "READY", "UYGUN")):
        return False
    return not any(x in n for x in ("DEGIL", "BEKLE", "KORUMA", "ASIRI", "UZAM", "GEC GIRIS"))


def _extension(state: object, reasons: tuple[str, ...]) -> ExtensionState:
    n = _norm(" | ".join((str(state), *reasons)))
    if any(x in n for x in ("ASIRI UZAM", "COK UZAM", "GEC GIRIS", "KAR KORUMA", "OVEREXTEND")):
        return ExtensionState.SEVERE
    if any(x in n for x in ("UZAM", "TEMKIN", "CAUTION")):
        return ExtensionState.MILD
    return ExtensionState.CLEAN


def _rebound(risks: tuple[str, ...]) -> ReboundState:
    n = _norm(" | ".join(risks))
    rebound = any(x in n for x in ("REBOUND", "TEPKI YUKSEL", "TEPKI HAREK", "REAKSIYON"))
    if rebound and any(x in n for x in ("TRAP", "TUZAK", "FAIL", "BASARISIZ", "KIRILGAN")):
        return ReboundState.TRAP
    if rebound:
        return ReboundState.CAUTION
    return ReboundState.NO


def _contradictions(risks: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    hard, soft = [], []
    for risk in risks:
        n = _norm(risk)
        if any(x in n for x in (
            "HARD CONTRADICTION", "SERT CELISKI", "TREND NEGATIF",
            "DUSUS TREND", "YAPI BOZUL", "STRUCTURE BREAKDOWN", "ASAGI KIRIL",
        )):
            hard.append(risk)
        else:
            soft.append(risk)
    return tuple(dict.fromkeys(hard)), tuple(dict.fromkeys(soft))


def _ordinal(values: dict[str, float], reverse: bool) -> dict[str, int]:
    ordered = sorted(values.items(), key=lambda kv: ((-kv[1]) if reverse else kv[1], kv[0]))
    return {symbol: idx for idx, (symbol, _) in enumerate(ordered, 1)}


def build_next_day_candidate_evidence(
    *,
    scan_result: object,
    visibility_contexts: Iterable[object] = (),
) -> tuple[NextDayCandidateEvidence, ...]:
    rows = _tuple(getattr(scan_result, "tum_sonuclar", None))
    if not rows:
        raise NextDayRuntimeObserverError("CANONICAL_FULL_RESULT_EMPTY_OR_MISSING")

    canonical_date = _canonical_date(scan_result, rows)
    visibility = _visibility_index(visibility_contexts)
    freshness = getattr(scan_result, "veri_tazeligi", None)
    freshness_valid = bool(freshness is not None and not bool(getattr(freshness, "kilitli", True)))

    blocked = {
        _sym(x) for x in _tuple(getattr(scan_result, "vbts_engellenen_semboller", ())) if _sym(x)
    }
    block_reasons = getattr(scan_result, "vbts_engelleme_nedenleri", {}) or {}
    if hasattr(block_reasons, "keys"):
        blocked.update(_sym(x) for x in block_reasons.keys() if _sym(x))

    evren = _norm(getattr(scan_result, "evren_adi", ""))
    source = str(getattr(scan_result, "evren_kaynagi", "") or "").strip()
    try:
        size = int(getattr(scan_result, "evren_sembol_sayisi", 0))
    except (TypeError, ValueError):
        size = 0
    universe_comparable = ("BIST" in evren and "TUM" in evren and bool(source) and size > 0)

    raw: list[dict[str, object]] = []
    migration_values: dict[str, float] = {}
    momentum_values: dict[str, float] = {}
    readiness_values: dict[str, float] = {}

    for research_rank, item in enumerate(rows, 1):
        symbol = _sym(getattr(item, "sembol", getattr(item, "symbol", "")))
        if not symbol:
            continue

        signal = getattr(item, "sinyal", None)
        pos = tuple(str(x).strip() for x in _tuple(getattr(signal, "pozitif_nedenler", ())) if str(x).strip())
        risks = tuple(str(x).strip() for x in _tuple(getattr(signal, "riskler", ())) if str(x).strip())

        families: list[str] = []
        explanation: list[str] = []
        context = visibility.get(symbol)

        if _f1_positive(context):
            families.append("F1")
            explanation.append("F1: existing rank migration / visibility context")
        try:
            change = float(getattr(context, "rank_change"))
            if change > 0:
                migration_values[symbol] = change
        except (AttributeError, TypeError, ValueError):
            pass

        hits = _reason_families(pos)
        for family in ("F2", "F3", "F5"):
            if hits[family]:
                families.append(family)
                explanation.append(f"{family}: {'; '.join(hits[family])}")

        try:
            momentum_values[symbol] = float(getattr(signal, "momentum_puani"))
        except (AttributeError, TypeError, ValueError):
            pass

        try:
            readiness = evaluate_jump_candidate_entry_readiness(item)
        except Exception:
            readiness = None

        readiness_state = getattr(readiness, "state", "") if readiness is not None else ""
        readiness_reasons = tuple(
            str(x).strip() for x in _tuple(getattr(readiness, "reasons", ())) if str(x).strip()
        )
        if readiness is not None and _readiness_positive(readiness_state):
            families.append("F4")
            explanation.append(f"F4: {readiness_state}")
            levels = getattr(item, "destek_direnc", None)
            try:
                readiness_values[symbol] = float(getattr(levels, "direnc_uzaklik_yuzde"))
            except (AttributeError, TypeError, ValueError):
                pass

        hard, soft = _contradictions(risks)
        ext = _extension(readiness_state, readiness_reasons)
        reb = _rebound(risks)
        analysis_date = str(getattr(item, "analiz_tarihi", "") or "")
        data_ready = bool(signal is not None and analysis_date[:10] == canonical_date)
        family_tuple = tuple(dict.fromkeys(families))

        raw.append({
            "canonical_date": canonical_date,
            "symbol": symbol,
            "research_rank": research_rank,
            "evidence_families": family_tuple,
            "data_ready": data_ready,
            "freshness_valid": freshness_valid,
            "security_lock": symbol in blocked,
            "universe_comparable": universe_comparable,
            "research_valid": signal is not None,
            "hard_contradictions": hard,
            "soft_contradictions": soft,
            "extension": ext,
            "rebound": reb,
            "single_factor_domination": len(family_tuple) <= 1,
            "explanation": " | ".join(explanation) or "No independent F1-F5 evidence mapped.",
            "warnings": tuple(dict.fromkeys((*soft, *readiness_reasons))),
        })

    if not raw:
        raise NextDayRuntimeObserverError("NO_VALID_SYMBOL_ROWS")

    migration_rank = _ordinal(migration_values, True)
    relative_strength_rank = _ordinal(momentum_values, True)
    readiness_rank = _ordinal(readiness_values, False)

    return tuple(
        NextDayCandidateEvidence(
            **item,
            migration_rank=migration_rank.get(str(item["symbol"]), 99),
            relative_strength_rank=relative_strength_rank.get(str(item["symbol"]), 99),
            readiness_rank=readiness_rank.get(str(item["symbol"]), 99),
        )
        for item in raw
    )


def observe_canonical_next_day_selection(
    *,
    scan_result: object,
    visibility_contexts: Iterable[object] = (),
) -> NextDayRuntimeObserverResult:
    evidence = build_next_day_candidate_evidence(
        scan_result=scan_result,
        visibility_contexts=visibility_contexts,
    )
    selection = select_next_day_candidates(evidence)
    # NEXT_DAY_PHASE8_T1_OUTCOME_SETTLEMENT_V1
    try:
        settle_pending_next_day_outcomes(
            current_date=evidence[0].canonical_date if evidence else "",
        )
    except Exception:
        pass
    # NEXT_DAY_CANONICAL_RANK_SNAPSHOT_P0_V1
    # Reuse the exact ordered tum_sonuclar already used
    # by Next-Day evidence mapping. No second scan/ranking.
    _rank_source_rows = _tuple(
        getattr(scan_result, "tum_sonuclar", None)
    )
    if not _rank_source_rows:
        raise NextDayRuntimeObserverError(
            "CANONICAL_RANK_SOURCE_EMPTY"
        )
    _rank_payload_rows = tuple(
        {
            "Hisse": _sym(getattr(item, "sembol", getattr(item, "symbol", ""))),
            "S?ra": rank,
        }
        for rank, item in enumerate(
            _rank_source_rows,
            start=1,
        )
    )
    if (
        len(_rank_payload_rows) != len(_rank_source_rows)
        or any(not row['Hisse'] for row in _rank_payload_rows)
        or len({row['Hisse'] for row in _rank_payload_rows})
           != len(_rank_payload_rows)
    ):
        raise NextDayRuntimeObserverError(
            "CANONICAL_RANK_ROWS_INVALID"
        )
    _profile_name = str(
        getattr(
            getattr(scan_result, "profil", None),
            "adi",
            "",
        )
        or "dengeli"
    ).strip()
    _universe_source = str(
        getattr(scan_result, "evren_kaynagi", "") or ""
    ).strip()
    if not _universe_source:
        raise NextDayRuntimeObserverError(
            "CANONICAL_RANK_UNIVERSE_SOURCE_MISSING"
        )
    _selected_symbols = {
        _sym(item.symbol)
        for item in tuple(selection.primary) + tuple(selection.reserve)
        if _sym(item.symbol)
    }
    _rank_symbols = {
        row['Hisse']
        for row in _rank_payload_rows
    }
    if not _selected_symbols.issubset(_rank_symbols):
        raise NextDayRuntimeObserverError(
            "SELECTION_NOT_SUBSET_OF_CANONICAL_RANK_UNIVERSE"
        )
    persist_research_rank_snapshot(
        rows=_rank_payload_rows,
        as_of=selection.canonical_date,
        universe_source=_universe_source,
        profile_name=(
            "NEXT_DAY_CANONICAL_FULL_V1|"
            + _profile_name
        ),
    )
    status = persist_frozen_selection(selection)
    # WEEKLY_OPPORTUNITY_W2_W6_RUNTIME_HOOK_V1
    try:
        observe_weekly_opportunity_runtime(
            scan_result=scan_result,
            evidence=evidence,
            selection=selection,
        )
    except Exception:
        pass
    return NextDayRuntimeObserverResult(
        canonical_date=selection.canonical_date,
        candidate_count=len(evidence),
        primary_count=len(selection.primary),
        reserve_count=len(selection.reserve),
        persistence_status=status,
    )
