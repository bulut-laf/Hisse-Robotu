from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Iterable, Mapping, Sequence

import pandas as pd

from .backtest_models import BacktestTrade
from .portfolio_backtest import (
    PortfolioBacktestAnalyzer,
    PortfolioBacktestConfig,
    PortfolioBacktestReport,
)


class PortfolioCapacitySensitivityError(ValueError):
    """Portföy kapasite duyarlılığı girdileri geçersizdir."""


@dataclass(frozen=True)
class PortfolioCapacityScenario:
    """Tek bir eş zamanlı pozisyon kapasitesinin sonucu."""

    kapasite: int
    pozisyon_basina_sermaye_orani: float
    rapor: PortfolioBacktestReport

    @property
    def getiri_dusus_orani(self) -> float | None:
        dusus = self.rapor.maksimum_dusus_orani

        if isclose(dusus, 0.0, abs_tol=1e-12):
            return None

        return self.rapor.toplam_getiri_orani / dusus


@dataclass(frozen=True)
class PortfolioCapacitySensitivityReport:
    """Aynı veri ve işlemlerle çalıştırılan kapasite senaryoları."""

    senaryolar: tuple[PortfolioCapacityScenario, ...]

    @property
    def en_yuksek_getiri_senaryosu(self) -> PortfolioCapacityScenario | None:
        if not self.senaryolar:
            return None

        return max(
            self.senaryolar,
            key=lambda senaryo: (
                senaryo.rapor.toplam_getiri_orani,
                -senaryo.kapasite,
            ),
        )

    @property
    def en_dusuk_dusus_senaryosu(self) -> PortfolioCapacityScenario | None:
        if not self.senaryolar:
            return None

        return min(
            self.senaryolar,
            key=lambda senaryo: (
                senaryo.rapor.maksimum_dusus_orani,
                senaryo.kapasite,
            ),
        )

    @property
    def en_iyi_getiri_dusus_senaryosu(
        self,
    ) -> PortfolioCapacityScenario | None:
        uygunlar = tuple(
            senaryo
            for senaryo in self.senaryolar
            if senaryo.getiri_dusus_orani is not None
        )

        if not uygunlar:
            return None

        return max(
            uygunlar,
            key=lambda senaryo: (
                float(senaryo.getiri_dusus_orani),
                -senaryo.kapasite,
            ),
        )


class PortfolioCapacitySensitivityAnalyzer:
    """
    Aynı fiyat verileri ve aynı önceden üretilmiş işlemler üzerinde
    farklı eş zamanlı pozisyon kapasitelerini karşılaştırır.

    Her kapasitede pozisyon başına sermaye oranı otomatik olarak
    ``1 / kapasite`` seçilir. Böylece tüm senaryolar kaldıraçsız ve
    karşılaştırılabilir kalır.
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
        kapasiteler: Sequence[int] = (1, 2, 3),
        baslangic_sermayesi: float = 100_000.0,
        islem_maliyeti_orani: float = 0.001,
    ) -> PortfolioCapacitySensitivityReport:
        hazir_kapasiteler = self._kapasiteleri_dogrula(kapasiteler)
        hazir_islemler = tuple(islemler)
        senaryolar: list[PortfolioCapacityScenario] = []

        for kapasite in hazir_kapasiteler:
            ayarlar = PortfolioBacktestConfig(
                baslangic_sermayesi=baslangic_sermayesi,
                maksimum_es_zamanli_pozisyon=kapasite,
                pozisyon_basina_sermaye_orani=None,
                islem_maliyeti_orani=islem_maliyeti_orani,
            )
            rapor = self._portfoy_analizcisi.analiz_et(
                fiyat_verileri=fiyat_verileri,
                islemler=hazir_islemler,
                yapilandirma=ayarlar,
            )
            senaryolar.append(
                PortfolioCapacityScenario(
                    kapasite=kapasite,
                    pozisyon_basina_sermaye_orani=float(
                        ayarlar.pozisyon_basina_sermaye_orani
                    ),
                    rapor=rapor,
                )
            )

        return PortfolioCapacitySensitivityReport(
            senaryolar=tuple(senaryolar)
        )

    @staticmethod
    def _kapasiteleri_dogrula(
        kapasiteler: Sequence[int],
    ) -> tuple[int, ...]:
        if isinstance(kapasiteler, (str, bytes)):
            raise PortfolioCapacitySensitivityError(
                "Kapasiteler pozitif tam sayı dizisi olmalıdır."
            )

        try:
            hazir = tuple(kapasiteler)
        except TypeError as hata:
            raise PortfolioCapacitySensitivityError(
                "Kapasiteler pozitif tam sayı dizisi olmalıdır."
            ) from hata

        if not hazir:
            raise PortfolioCapacitySensitivityError(
                "En az bir portföy kapasitesi verilmelidir."
            )

        if any(
            isinstance(kapasite, bool)
            or not isinstance(kapasite, int)
            or kapasite <= 0
            for kapasite in hazir
        ):
            raise PortfolioCapacitySensitivityError(
                "Portföy kapasiteleri pozitif tam sayı olmalıdır."
            )

        if len(set(hazir)) != len(hazir):
            raise PortfolioCapacitySensitivityError(
                "Portföy kapasiteleri tekrar etmemelidir."
            )

        return tuple(sorted(hazir))
