from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from backend.app.prebreakout.prebreakout_live_watch import canli_sinyalleri_kaydet
from backend.app.prebreakout.prebreakout_models import PreBreakoutResult, PreBreakoutStage
from backend.app.prebreakout.prebreakout_threshold_policy import PreBreakoutThresholdPolicy


@dataclass(frozen=True)
class _Features:
    close: float = 100.0
    direnc_uzaklik_pct: float = 1.0
    rsi14: float = 58.0
    rsi_egimi: float = 1.0
    macd_histogram: float = 0.5
    macd_histogram_egimi: float = 0.2
    momentum_skoru: float = 14.0
    hacim_orani_3_10: float = 1.2
    atr_daralma_orani: float = 0.8
    son_gun_getirisi_pct: float = 1.0
    risk_odul: float = 2.2


def _result(stage: PreBreakoutStage = PreBreakoutStage.E3) -> PreBreakoutResult:
    return PreBreakoutResult(
        symbol="TUPRS.IS", score=75, stage=stage, stage_label="Yakın", features=_Features(),
        component_scores=None, late_entry=False, accepted=True, reasons=(), risks=(),
    )


def test_farkli_asama_olsa_da_bekleme_suresinde_tekrar_yazilmaz(tmp_path: Path) -> None:
    target = tmp_path / "live.jsonl"
    policy = PreBreakoutThresholdPolicy()
    first = canli_sinyalleri_kaydet([_result()], date(2026, 8, 1), policy, path=target)
    second = canli_sinyalleri_kaydet(
        [_result(PreBreakoutStage.E4)], date(2026, 8, 4), policy, path=target
    )
    third = canli_sinyalleri_kaydet(
        [_result(PreBreakoutStage.E4)], date(2026, 8, 7), policy, path=target
    )
    assert len(first) == 1
    assert second == ()
    assert len(third) == 1
