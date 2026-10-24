from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..analysis.position_monitor import (
    OpenPosition,
    PositionMonitoringResult,
    PositionMonitorError,
    acik_pozisyonu_izle,
)
from ..analysis.technical_confirmation import (
    MultiTimeframeTechnicalConfirmation,
    TechnicalConfirmationError,
    teknik_teyit_analizi_yap,
)
from ..analysis.trade_plan import (
    TradePlan,
    TradePlanError,
    islem_plani_olustur,
)
from ..data.data_freshness import DataFreshnessResult, gunluk_veri_tazeligini_degerlendir
from ..data.multi_timeframe_data import (
    MultiTimeframeDataBundle,
    MultiTimeframeDataError,
    bist_sembolunu_hazirla,
    coklu_zaman_dilimi_verisi_getir,
)


class LiveAnalysisDashboardError(Exception):
    """Güncel analiz ekranı sonucu hazırlanamadığında kullanılır."""


@dataclass(frozen=True)
class LiveAnalysisRequest:
    """Güncel teknik analiz ve işlem planı için kullanıcı girdileri."""

    sembol: str
    sermaye: float = 100_000.0
    azami_risk_orani: float = 0.01

    def __post_init__(self) -> None:
        object.__setattr__(self, "sembol", bist_sembolunu_hazirla(self.sembol))
        if self.sermaye <= 0:
            raise ValueError("Sermaye pozitif olmalıdır.")
        if not 0 < self.azami_risk_orani <= 1:
            raise ValueError("Azami risk oranı 0 ile 1 arasında olmalıdır.")


@dataclass(frozen=True)
class LiveAnalysisResult:
    """Aynı veri paketiyle üretilmiş teknik teyit ve işlem planı."""

    paket: MultiTimeframeDataBundle
    teknik_teyit: MultiTimeframeTechnicalConfirmation
    islem_plani: TradePlan
    veri_tazeligi: DataFreshnessResult | None = None


@dataclass(frozen=True)
class OpenPositionDashboardRequest:
    """Açık pozisyon izleme ekranının kullanıcı girdileri."""

    sembol: str
    giris_tarihi: object
    giris_fiyati: float
    lot_sayisi: int
    ilk_stop: float
    hedef_1: float
    hedef_2: float
    mevcut_stop: float | None = None
    hedef_1_gerceklesti: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "sembol", bist_sembolunu_hazirla(self.sembol))

    def pozisyon_olustur(self) -> OpenPosition:
        return OpenPosition(
            giris_tarihi=self.giris_tarihi,
            giris_fiyati=float(self.giris_fiyati),
            lot_sayisi=int(self.lot_sayisi),
            ilk_stop=float(self.ilk_stop),
            hedef_1=float(self.hedef_1),
            hedef_2=float(self.hedef_2),
            mevcut_stop=(
                None if self.mevcut_stop is None else float(self.mevcut_stop)
            ),
            hedef_1_gerceklesti=bool(self.hedef_1_gerceklesti),
        )


DataLoader = Callable[[str], MultiTimeframeDataBundle]
TechnicalEngine = Callable[
    [MultiTimeframeDataBundle],
    MultiTimeframeTechnicalConfirmation,
]
TradePlanEngine = Callable[..., TradePlan]
PositionMonitorEngine = Callable[..., PositionMonitoringResult]


class LiveAnalysisDashboardService:
    """Veriyi bir kez indirip güncel teknik analiz ve planı birlikte üretir."""

    def __init__(
        self,
        veri_getirici: DataLoader = coklu_zaman_dilimi_verisi_getir,
        teknik_motoru: TechnicalEngine = teknik_teyit_analizi_yap,
        plan_motoru: TradePlanEngine = islem_plani_olustur,
    ) -> None:
        self._veri_getirici = veri_getirici
        self._teknik_motoru = teknik_motoru
        self._plan_motoru = plan_motoru

    def calistir(self, istek: LiveAnalysisRequest) -> LiveAnalysisResult:
        try:
            paket = self._veri_getirici(istek.sembol)
            teknik_teyit = self._teknik_motoru(paket)
            veri_tazeligi = None
            if hasattr(paket, "getir"):
                veri_tazeligi = gunluk_veri_tazeligini_degerlendir(
                    paket.getir("Günlük").veri
                )
            islem_plani = self._plan_motoru(
                paket=paket,
                teknik_teyit=teknik_teyit,
                sermaye=istek.sermaye,
                azami_risk_orani=istek.azami_risk_orani,
            )
        except (
            MultiTimeframeDataError,
            TechnicalConfirmationError,
            TradePlanError,
            ValueError,
        ) as hata:
            raise LiveAnalysisDashboardError(str(hata)) from hata

        return LiveAnalysisResult(
            paket=paket,
            teknik_teyit=teknik_teyit,
            islem_plani=islem_plani,
            veri_tazeligi=veri_tazeligi,
        )


class OpenPositionDashboardService:
    """Aynı veri ve teknik teyitle açık pozisyon izleme sonucu üretir."""

    def __init__(
        self,
        veri_getirici: DataLoader = coklu_zaman_dilimi_verisi_getir,
        teknik_motoru: TechnicalEngine = teknik_teyit_analizi_yap,
        izleme_motoru: PositionMonitorEngine = acik_pozisyonu_izle,
    ) -> None:
        self._veri_getirici = veri_getirici
        self._teknik_motoru = teknik_motoru
        self._izleme_motoru = izleme_motoru

    def calistir(
        self,
        istek: OpenPositionDashboardRequest,
    ) -> PositionMonitoringResult:
        try:
            paket = self._veri_getirici(istek.sembol)
            teknik_teyit = self._teknik_motoru(paket)
            return self._izleme_motoru(
                paket=paket,
                teknik_teyit=teknik_teyit,
                pozisyon=istek.pozisyon_olustur(),
            )
        except (
            MultiTimeframeDataError,
            TechnicalConfirmationError,
            PositionMonitorError,
            ValueError,
        ) as hata:
            raise LiveAnalysisDashboardError(str(hata)) from hata
