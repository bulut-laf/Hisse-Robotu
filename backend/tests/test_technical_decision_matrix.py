from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pandas as pd

from backend.app.analysis.divergence_analysis import (
    DivergenceKind,
    DivergenceSignal,
    PivotPoint,
    TimeframeDivergenceResult,
)
from backend.app.analysis.technical_decision_matrix import (
    DecisionClass,
    DecisionMatrixContext,
    MatrixDirection,
    build_technical_decision_matrix,
    decision_matrix_rows,
)


def divergence(
    timeframe: str,
    kind: DivergenceKind | None = None,
) -> TimeframeDivergenceResult:
    signals = ()
    if kind is not None:
        first = PivotPoint(
            10,
            pd.Timestamp("2026-01-01"),
            100.0,
            40.0,
        )
        second = PivotPoint(
            20,
            pd.Timestamp("2026-02-01"),
            105.0,
            50.0,
        )
        signals = (
            DivergenceSignal(
                timeframe=timeframe,
                oscillator="RSI",
                kind=kind,
                first=first,
                second=second,
                price_change_percent=5.0,
                oscillator_change=10.0,
                volume_confirmation=True,
                confidence_score=80,
                confidence_level="Yüksek",
                explanation="test",
            ),
        )
    return TimeframeDivergenceResult(
        timeframe=timeframe,
        latest_timestamp=pd.Timestamp("2026-02-01"),
        signals=signals,
        summary="test",
        positive_count=1 if kind in {
            DivergenceKind.NORMAL_POSITIVE,
            DivergenceKind.HIDDEN_POSITIVE,
        } else 0,
        negative_count=1 if kind in {
            DivergenceKind.NORMAL_NEGATIVE,
            DivergenceKind.HIDDEN_NEGATIVE,
        } else 0,
    )


def timeframe(
    *,
    yon: str,
    skor: int,
    momentum: str,
    volume: bool,
):
    return SimpleNamespace(
        yon=yon,
        skor=skor,
        kapanis=100.0,
        destek=95.0,
        direnc=112.0,
        momentum=SimpleNamespace(durum=momentum),
        kirilim=SimpleNamespace(hacim_teyidi=volume),
    )


def technical(
    *,
    daily="Pozitif",
    weekly="Pozitif",
):
    return SimpleNamespace(
        sembol="THYAO.IS",
        gunluk=timeframe(
            yon=daily,
            skor=80,
            momentum="Pozitif",
            volume=True,
        ),
        haftalik=timeframe(
            yon=weekly,
            skor=82,
            momentum="Pozitif",
            volume=True,
        ),
    )


def plan(
    *,
    decision="İşlem Var",
    rr1=2.1,
    rr2=3.0,
    atr=2.4,
):
    return SimpleNamespace(
        sembol="THYAO.IS",
        karar=decision,
        plan_tipi="Onaylı Alım Planı",
        risk_odul_1=rr1,
        risk_odul_2=rr2,
        atr_yuzde=atr,
    )


def test_pozitif_gunluk_haftalik_yapi_izlemeye_degerdir():
    result = build_technical_decision_matrix(
        technical(),
        plan(),
        divergence("Günlük", DivergenceKind.NORMAL_POSITIVE),
        divergence("Haftalık", DivergenceKind.HIDDEN_POSITIVE),
        context=DecisionMatrixContext(
            market_regime="Pozitif",
            sector_outlook="Olumlu",
            relative_strength="Güçlü",
        ),
    )

    assert result.classification == DecisionClass.WATCH_WORTHY
    assert result.quality_score >= 70


def test_negatif_haftalik_trend_uygun_degil_kilidi_uygular():
    result = build_technical_decision_matrix(
        technical(weekly="Negatif"),
        plan(),
        divergence("Günlük"),
        divergence("Haftalık"),
    )

    assert result.classification == DecisionClass.NOT_SUITABLE


def test_islem_plani_yoksa_uygun_degil():
    result = build_technical_decision_matrix(
        technical(),
        plan(decision="İşlem Yok", rr1=None, rr2=None),
        divergence("Günlük"),
        divergence("Haftalık"),
    )

    assert result.classification == DecisionClass.NOT_SUITABLE


def test_eksik_piyasa_sektor_baglamlari_tahmin_edilmez():
    result = build_technical_decision_matrix(
        technical(),
        plan(),
        divergence("Günlük"),
        divergence("Haftalık"),
    )

    context_rows = {
        row.component: row
        for row in result.rows
        if row.component in {
            "Piyasa rejimi",
            "Sektör görünümü",
            "Göreceli güç",
        }
    }

    assert all(
        row.direction == MatrixDirection.UNAVAILABLE
        for row in context_rows.values()
    )
    assert all(
        row.daily == "Bağlam aktarılmadı"
        for row in context_rows.values()
    )


def test_olumlu_ve_olumsuz_gerekceler_ayri_tutulur():
    result = build_technical_decision_matrix(
        technical(),
        plan(atr=8.0),
        divergence("Günlük", DivergenceKind.NORMAL_NEGATIVE),
        divergence("Haftalık", DivergenceKind.NORMAL_NEGATIVE),
    )

    assert result.positive_reasons
    assert result.negative_reasons


def test_tek_al_skoru_ve_tavsiye_uretmez():
    result = build_technical_decision_matrix(
        technical(),
        plan(),
        divergence("Günlük"),
        divergence("Haftalık"),
    )

    assert result.classification.value in {
        "İzlemeye Değer",
        "Temkinli İzle",
        "Uygun Değil",
    }
    assert "alım veya satım tavsiyesi üretmez" in result.disclaimer


def test_tablo_satirlari_gunluk_ve_haftalik_sutunlari_icerir():
    result = build_technical_decision_matrix(
        technical(),
        plan(),
        divergence("Günlük"),
        divergence("Haftalık"),
    )

    rows = decision_matrix_rows(result)

    assert rows
    assert {"Bileşen", "Günlük", "Haftalık", "Yön", "Katkı"} <= set(
        rows[0]
    )


def test_farkli_semboller_reddedilir():
    mismatched = SimpleNamespace(**vars(plan()))
    mismatched.sembol = "EREGL.IS"

    try:
        build_technical_decision_matrix(
            technical(),
            mismatched,
            divergence("Günlük"),
            divergence("Haftalık"),
        )
    except ValueError as error:
        assert "aynı sembole" in str(error)
    else:
        raise AssertionError("Farklı sembol reddedilmeliydi.")
