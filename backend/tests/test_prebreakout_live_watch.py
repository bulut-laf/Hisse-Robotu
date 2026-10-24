from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path

import pytest

from backend.app.prebreakout.prebreakout_live_watch import (
    canli_sinyal_olustur,
    canli_sinyalleri_kaydet,
    canli_sinyalleri_yukle,
)
from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutResult,
    PreBreakoutStage,
)
from backend.app.prebreakout.prebreakout_threshold_policy import (
    PreBreakoutThresholdPolicy,
)


@dataclass(frozen=True)
class _LiveWatchFeatures:
    close: float = 187.5
    direnc_uzaklik_pct: float = 1.8
    rsi14: float = 58.0
    rsi_egimi: float = 1.2
    macd_histogram: float = 0.7
    macd_histogram_egimi: float = 0.25
    momentum_skoru: float = 14.0
    hacim_orani_3_10: float = 1.35
    atr_daralma_orani: float = 0.82
    son_gun_getirisi_pct: float = 1.1
    risk_odul: float = 2.4


@pytest.fixture
def tuprs_prebreakout_result() -> PreBreakoutResult:
    return PreBreakoutResult(
        symbol="TUPRS.IS",
        score=78,
        stage=PreBreakoutStage.E3,
        stage_label="Tetiklenmeye yakın",
        features=_LiveWatchFeatures(),
        component_scores=None,
        late_entry=False,
        accepted=True,
        reasons=("Momentum ve RSI eğimi olumlu.",),
        risks=(),
    )


def test_canli_sinyal_yalnizca_e2_e4_icin_olusturulur(tuprs_prebreakout_result) -> None:
    policy = PreBreakoutThresholdPolicy(enabled=True, stage_minimum_momentum_scores={"E3": 12})
    signal = canli_sinyal_olustur(
        tuprs_prebreakout_result,
        date(2026, 8, 1),
        policy,
        recorded_at=datetime(2026, 8, 1, 8, 30, tzinfo=timezone.utc),
    )
    assert signal is not None
    assert signal.stage in {"E2", "E3", "E4"}
    assert signal.signal_date == "2026-08-01"
    assert signal.minimum_momentum_score == policy.minimum_momentum_score(signal.stage)
    assert signal.payload_sha256


def test_ayni_sinyal_ikinci_kez_yazilmaz(tmp_path: Path, tuprs_prebreakout_result) -> None:
    target = tmp_path / "live.jsonl"
    policy = PreBreakoutThresholdPolicy()
    first = canli_sinyalleri_kaydet(
        [tuprs_prebreakout_result], date(2026, 8, 1), policy, path=target
    )
    second = canli_sinyalleri_kaydet(
        [tuprs_prebreakout_result], date(2026, 8, 1), policy, path=target
    )
    assert len(first) == 1
    assert second == ()
    assert len(canli_sinyalleri_yukle(target)) == 1


def test_kayit_butunluk_degisikligini_reddeder(tmp_path: Path, tuprs_prebreakout_result) -> None:
    target = tmp_path / "live.jsonl"
    canli_sinyalleri_kaydet(
        [tuprs_prebreakout_result],
        date(2026, 8, 1),
        PreBreakoutThresholdPolicy(),
        path=target,
    )
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["score"] = int(payload["score"]) + 1
    target.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="bütünlük"):
        canli_sinyalleri_yukle(target)
