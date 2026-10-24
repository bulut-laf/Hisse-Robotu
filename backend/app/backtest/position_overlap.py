from __future__ import annotations

from datetime import date

from .backtest_engine import (
    BacktestResult,
    SkippedSignal,
)
from .backtest_models import (
    BacktestConfig,
    BacktestMetrics,
    BacktestSignal,
    BacktestTrade,
)


CAKISMA_NEDENI = (
    "Aynı sembolde açık pozisyon var."
)


def cakisan_islemleri_filtrele(
    sonuc: BacktestResult,
    yapilandirma: BacktestConfig,
) -> BacktestResult:
    """
    Aynı sembolde açık pozisyon varken başlayan yeni işlemleri atlar.

    Farklı sembollerde aynı tarihlerde açık işlemler bulunabilir.
    Önceki işlemin çıkış tarihiyle aynı gün başlayan yeni işlem de
    çakışan işlem kabul edilir.

    Filtre sonrasında performans metrikleri kabul edilen işlemler
    üzerinden yeniden hesaplanır.
    """
    sirali_islemler = sorted(
        sonuc.islemler,
        key=lambda islem: (
            islem.giris_tarihi,
            islem.sembol,
            islem.sinyal_tarihi,
            islem.cikis_tarihi,
        ),
    )

    kabul_edilenler: list[BacktestTrade] = []
    cakisma_nedeniyle_atlananlar: list[
        SkippedSignal
    ] = []

    son_cikis_tarihleri: dict[str, date] = {}

    for islem in sirali_islemler:
        onceki_cikis_tarihi = (
            son_cikis_tarihleri.get(
                islem.sembol
            )
        )

        if (
            onceki_cikis_tarihi is not None
            and islem.giris_tarihi
            <= onceki_cikis_tarihi
        ):
            cakisma_nedeniyle_atlananlar.append(
                SkippedSignal(
                    sinyal=_islemden_sinyal_olustur(
                        islem
                    ),
                    neden=(
                        f"{CAKISMA_NEDENI} "
                        "Mevcut pozisyonun çıkış tarihi: "
                        f"{onceki_cikis_tarihi.isoformat()}."
                    ),
                )
            )
            continue

        kabul_edilenler.append(
            islem
        )

        son_cikis_tarihleri[
            islem.sembol
        ] = islem.cikis_tarihi

    kabul_edilen_islemler = tuple(
        kabul_edilenler
    )

    metrikler = BacktestMetrics.hesapla(
        islemler=kabul_edilen_islemler,
        yapilandirma=yapilandirma,
    )

    return BacktestResult(
        islemler=kabul_edilen_islemler,
        atlanan_sinyaller=(
            sonuc.atlanan_sinyaller
            + tuple(
                cakisma_nedeniyle_atlananlar
            )
        ),
        metrikler=metrikler,
    )


def _islemden_sinyal_olustur(
    islem: BacktestTrade,
) -> BacktestSignal:
    return BacktestSignal(
        sembol=islem.sembol,
        sinyal_tarihi=islem.sinyal_tarihi,
        skor=islem.skor,
        teknik_gorunum=(
            islem.teknik_gorunum
        ),
    )