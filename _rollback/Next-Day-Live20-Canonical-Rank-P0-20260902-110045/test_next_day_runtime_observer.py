from __future__ import annotations

import ast
import inspect
from pathlib import Path
from types import SimpleNamespace

import backend.app.analysis.next_day_runtime_observer as observer


def _candidate(symbol="AAA.IS", reasons=None, risks=()):
    return SimpleNamespace(
        sembol=symbol,
        analiz_tarihi="2026-08-29T18:10:00+03:00",
        sinyal=SimpleNamespace(
            momentum_puani=18,
            trend_puani=12,
            pozitif_nedenler=tuple(reasons or (
                "Trend yapısı pozitif",
                "Momentum MACD ile güçleniyor",
                "Hacim teyidi mevcut",
            )),
            riskler=tuple(risks),
        ),
        destek_direnc=SimpleNamespace(direnc_uzaklik_yuzde=1.2),
    )


def _scan(*candidates, locked=False, blocked=()):
    return SimpleNamespace(
        evren_adi="BIST Tüm",
        evren_kaynagi="TEST_CANONICAL",
        evren_tarihi="2026-08-29",
        evren_sembol_sayisi=max(1, len(candidates)),
        tum_sonuclar=tuple(candidates),
        veri_tazeligi=SimpleNamespace(kilitli=locked),
        vbts_engellenen_semboller=tuple(blocked),
        vbts_engelleme_nedenleri={},
    )


def _visibility(symbol="AAA", change=5):
    return SimpleNamespace(symbol=symbol, visibility_state="IMPROVING", rank_change=change)


def _ready():
    return SimpleNamespace(state="HAZIR", reasons=("Mevcut giriş hazırlığı olumlu.",), extension_atr=0.0)


def test_mapping_deduplicates_existing_family_evidence(monkeypatch):
    monkeypatch.setattr(observer, "evaluate_jump_candidate_entry_readiness", lambda item: _ready())
    row = observer.build_next_day_candidate_evidence(
        scan_result=_scan(_candidate(reasons=(
            "Trend ve EMA yapısı pozitif",
            "Trend ve EMA yapısı pozitif",
            "Momentum RSI ve MACD ile pozitif",
            "Hacim teyidi güçlü",
            "Hacim teyidi güçlü",
        ))),
        visibility_contexts=(_visibility(),),
    )[0]
    assert row.evidence_families == ("F1", "F2", "F3", "F5", "F4")
    assert len(row.evidence_families) == len(set(row.evidence_families))


def test_existing_context_can_reach_primary_without_forced_fill(monkeypatch):
    saved = []
    monkeypatch.setattr(observer, "evaluate_jump_candidate_entry_readiness", lambda item: _ready())
    monkeypatch.setattr(observer, "persist_frozen_selection", lambda selection: saved.append(selection) or "APPENDED")
    result = observer.observe_canonical_next_day_selection(
        scan_result=_scan(_candidate()),
        visibility_contexts=(_visibility(),),
    )
    assert result.primary_count == 1
    assert result.reserve_count == 0
    assert len(saved) == 1


def test_freshness_and_security_fail_closed(monkeypatch):
    monkeypatch.setattr(observer, "evaluate_jump_candidate_entry_readiness", lambda item: _ready())
    stale = observer.build_next_day_candidate_evidence(
        scan_result=_scan(_candidate(), locked=True),
        visibility_contexts=(_visibility(),),
    )[0]
    blocked = observer.build_next_day_candidate_evidence(
        scan_result=_scan(_candidate(), blocked=("AAA.IS",)),
        visibility_contexts=(_visibility(),),
    )[0]
    assert stale.freshness_valid is False
    assert blocked.security_lock is True


def test_observer_has_no_scanner_new_store_new_score_or_trade_authority():
    source = inspect.getsource(observer)
    forbidden = (
        "BatchStockScanner",
        "BistUniverseRepository",
        ".scan(",
        ".calistir(",
        "yfinance",
        "requests.",
        "httpx.",
        "weighted_score",
        "composite_score",
        "position_size",
        "buy_order",
        "sell_order",
        "class NextDayRuntimeStore",
    )
    assert all(token not in source for token in forbidden)
    assert source.count("persist_frozen_selection(selection)") == 1
    assert "write_text(" not in source
    assert "open(" not in source


def test_runner_hook_is_evening_only_exception_isolated_and_after_candidate_snapshot():
    source = Path("backend/app/operations/daily_buy_decision_scheduled_runner.py").read_text(encoding="utf-8")
    assert source.count("# NEXT_DAY_PHASE7C_MINIMAL_OBSERVER_HOOK_V1") == 1
    assert "observe_canonical_next_day_selection(" in source
    assert 'str(phase).strip().upper() == "EVENING"' in source
    assert "except Exception:" in source

    tree = ast.parse(source)
    execute = next(
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name == "execute_scheduled_run"
    )
    observer_calls = [
        n for n in ast.walk(execute)
        if isinstance(n, ast.Call)
        and (
            (isinstance(n.func, ast.Name) and n.func.id == "observe_canonical_next_day_selection")
            or (isinstance(n.func, ast.Attribute) and n.func.attr == "observe_canonical_next_day_selection")
        )
    ]
    snapshot_calls = [
        n for n in ast.walk(execute)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "candidate_snapshot"
    ]
    assert len(observer_calls) == 1
    assert len(snapshot_calls) == 1
    assert observer_calls[0].lineno > snapshot_calls[0].lineno
