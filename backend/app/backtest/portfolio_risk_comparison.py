from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Iterable, Mapping

import pandas as pd

from .backtest_models import BacktestTrade
from .portfolio_backtest import (
    BOYUTLANDIRMA_RISK,
    BOYUTLANDIRMA_SABIT,
    PortfolioBacktestAnalyzer,
    PortfolioBacktestConfig,
    PortfolioBacktestReport,
)


@dataclass(frozen=True)
class PortfolioRiskScenario:
    """Tek bir portföy boyutlandırma yaklaşımının sonucu."""

    ad: str
    yapilandirma: PortfolioBacktestConfig
    rapor: PortfolioBacktestReport

    @property
    def getiri_dusus_orani(self) -> float | None:
        dusus = self.rapor.maksimum_dusus_orani
        if isclose(dusus, 0.0, abs_tol=1e-12):
            return None
        return self.rapor.toplam_getiri_orani / dusus

    @property
    def atlanma_nedenleri(self) -> tuple[tuple[str, int], ...]:
        sayilar: dict[str, int] = {}
        for kayit in self.rapor.atlanan_islemler:
            sayilar[kayit.neden] = sayilar.get(kayit.neden, 0) + 1
        return tuple(sorted(sayilar.items()))


@dataclass(frozen=True)
class PortfolioRiskComparisonReport:
    """Sabit sermaye ve risk bazlı pozisyon boyutlandırma karşılaştırması."""

    sabit: PortfolioRiskScenario
    risk_bazli: PortfolioRiskScenario

    @property
    def getiri_farki(self) -> float:
        return (
            self.risk_bazli.rapor.toplam_getiri_orani
            - self.sabit.rapor.toplam_getiri_orani
        )

    @property
    def maksimum_dusus_farki(self) -> float:
        return (
            self.risk_bazli.rapor.maksimum_dusus_orani
            - self.sabit.rapor.maksimum_dusus_orani
        )


class PortfolioRiskComparisonAnalyzer:
    """
    Aynı fiyat verileri ve aynı aday işlemler üzerinde sabit slot
    dağılımını risk bütçeli pozisyon boyutlandırmayla karşılaştırır.

    Risk bazlı senaryoda pozisyon büyüklüğü, giriş sermayesinin işlem
    başına risk bütçesi ile maliyet dahil stop kaybı arasındaki orana
    göre hesaplanır. Toplam açık risk sınırı aşılıyorsa işlem alınmaz.
    """

    def __init__(
        self,
        portfoy_analizcisi: PortfolioBacktestAnalyzer | None = None,
    ) -> None:
        self._portfoy_analizcisi = (
            portfoy_analizcisi
            if portfoy_analizcisi is not None
            else PortfolioBacktestAnalyzer()
        )

    def analiz_et(
        self,
        fiyat_verileri: Mapping[str, pd.DataFrame],
        islemler: Iterable[BacktestTrade],
        baslangic_sermayesi: float = 100_000.0,
        maksimum_es_zamanli_pozisyon: int = 3,
        islem_maliyeti_orani: float = 0.001,
        zarar_durdur_orani: float = 0.05,
        islem_basina_risk_orani: float = 0.01,
        toplam_acik_risk_orani: float = 0.02,
        maksimum_pozisyon_sermaye_orani: float | None = None,
    ) -> PortfolioRiskComparisonReport:
        hazir_islemler = tuple(islemler)
        sermaye_tavani = (
            maksimum_pozisyon_sermaye_orani
            if maksimum_pozisyon_sermaye_orani is not None
            else 1.0 / maksimum_es_zamanli_pozisyon
        )

        sabit_ayarlar = PortfolioBacktestConfig(
            baslangic_sermayesi=baslangic_sermayesi,
            maksimum_es_zamanli_pozisyon=maksimum_es_zamanli_pozisyon,
            pozisyon_basina_sermaye_orani=sermaye_tavani,
            islem_maliyeti_orani=islem_maliyeti_orani,
            boyutlandirma_modu=BOYUTLANDIRMA_SABIT,
            zarar_durdur_orani=zarar_durdur_orani,
        )
        risk_ayarlari = PortfolioBacktestConfig(
            baslangic_sermayesi=baslangic_sermayesi,
            maksimum_es_zamanli_pozisyon=maksimum_es_zamanli_pozisyon,
            pozisyon_basina_sermaye_orani=sermaye_tavani,
            islem_maliyeti_orani=islem_maliyeti_orani,
            boyutlandirma_modu=BOYUTLANDIRMA_RISK,
            zarar_durdur_orani=zarar_durdur_orani,
            islem_basina_risk_orani=islem_basina_risk_orani,
            toplam_acik_risk_orani=toplam_acik_risk_orani,
        )

        sabit_rapor = self._portfoy_analizcisi.analiz_et(
            fiyat_verileri=fiyat_verileri,
            islemler=hazir_islemler,
            yapilandirma=sabit_ayarlar,
        )
        risk_raporu = self._portfoy_analizcisi.analiz_et(
            fiyat_verileri=fiyat_verileri,
            islemler=hazir_islemler,
            yapilandirma=risk_ayarlari,
        )

        return PortfolioRiskComparisonReport(
            sabit=PortfolioRiskScenario(
                ad="Sabit sermaye",
                yapilandirma=sabit_ayarlar,
                rapor=sabit_rapor,
            ),
            risk_bazli=PortfolioRiskScenario(
                ad="Risk bazlı",
                yapilandirma=risk_ayarlari,
                rapor=risk_raporu,
            ),
        )
