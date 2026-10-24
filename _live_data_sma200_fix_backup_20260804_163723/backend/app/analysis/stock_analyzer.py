from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from ..data.market_data import (
    MarketDataError,
    fiyat_verisi_getir,
)
from ..indicators.technical_indicators import (
    IndicatorError,
    teknik_gostergeleri_ekle,
)
from ..risk.risk_engine import (
    RiskEngineError,
    RiskPlan,
    risk_plani_olustur,
)
from ..risk.structural_risk import (
    yapisal_risk_plani_olustur,
)
from .signal_engine import (
    SignalEngineError,
    SignalResult,
    sinyal_uret,
)
from .support_resistance import (
    SupportResistanceError,
    SupportResistanceResult,
    destek_direnc_bul,
)
from .volume_analysis import (
    VolumeAnalysisError,
    hacim_gostergelerini_ekle,
)


class StockAnalyzerError(Exception):
    """Bütünleşik hisse analizi sırasında oluşan özel hata."""


@dataclass(frozen=True)
class StockAnalysisResult:
    """Tek bir hisse için üretilen bütünleşik analiz sonucu."""

    sembol: str
    analiz_tarihi: str

    kapanis: float
    hacim: int

    ema9: float
    ema21: float
    rsi14: float

    macd: float
    macd_sinyal: float
    macd_histogram: float

    atr14: float
    atr_yuzde: float

    hacim_orani: float
    hacim_durumu: str

    destek_direnc: SupportResistanceResult
    hedef_kaynagi: str

    risk_plani: RiskPlan
    sinyal: SignalResult

    def sozluge_donustur(self) -> dict[str, Any]:
        """
        Sonucu API ve tablo katmanında kullanılabilecek
        sözlük biçimine dönüştürür.
        """
        return asdict(self)


class StockAnalyzer:
    """
    Piyasa verisi, teknik göstergeler, hacim, destek/direnç,
    risk ve sinyal modüllerini tek servis altında birleştirir.

    analiz_et:
        Güncel piyasa verisini indirerek analiz yapar.

    veriden_analiz_et:
        Yalnızca kendisine verilen fiyat penceresini analiz eder.
        Geçmiş backtest çalışmalarında bu metot kullanılır.
    """

    def analiz_et(
        self,
        sembol: str,
    ) -> StockAnalysisResult:
        """
        Piyasa verisini indirerek güncel hisse analizi yapar.
        """
        temiz_sembol = self._sembolu_temizle(
            sembol
        )

        try:
            fiyat_verisi = fiyat_verisi_getir(
                sembol=temiz_sembol,
                islem_gunu=160,
                indirme_donemi="1y",
                yalnizca_tamamlanmis_gunler=True,
            )

        except (
            ValueError,
            MarketDataError,
        ) as hata:
            raise StockAnalyzerError(
                f"{temiz_sembol} analiz edilemedi: {hata}"
            ) from hata

        return self.veriden_analiz_et(
            sembol=temiz_sembol,
            fiyat_verisi=fiyat_verisi,
        )

    def veriden_analiz_et(
        self,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
    ) -> StockAnalysisResult:
        """
        Yalnızca verilen OHLCV fiyat penceresini analiz eder.

        Bu metot veri indirme işlemi yapmaz. Bu nedenle geçmiş
        sinyal üretiminde gelecekteki fiyatların analize sızmasını
        önlemek için HistoricalSignalGenerator tarafından doğrudan
        kullanılabilir.
        """
        temiz_sembol = self._sembolu_temizle(
            sembol
        )

        if not isinstance(
            fiyat_verisi,
            pd.DataFrame,
        ):
            raise StockAnalyzerError(
                f"{temiz_sembol} analiz edilemedi: "
                "Fiyat verisi pandas DataFrame olmalıdır."
            )

        if fiyat_verisi.empty:
            raise StockAnalyzerError(
                f"{temiz_sembol} analiz edilemedi: "
                "Fiyat verisi boş olamaz."
            )

        try:
            return self._analiz_sonucunu_olustur(
                sembol=temiz_sembol,
                fiyat_verisi=fiyat_verisi.copy(),
            )

        except StockAnalyzerError:
            raise

        except (
            ValueError,
            IndicatorError,
            VolumeAnalysisError,
            SupportResistanceError,
            RiskEngineError,
            SignalEngineError,
        ) as hata:
            raise StockAnalyzerError(
                f"{temiz_sembol} analiz edilemedi: {hata}"
            ) from hata

    def _analiz_sonucunu_olustur(
        self,
        sembol: str,
        fiyat_verisi: pd.DataFrame,
    ) -> StockAnalysisResult:
        analiz = teknik_gostergeleri_ekle(
            fiyat_verisi
        )

        analiz = hacim_gostergelerini_ekle(
            analiz,
            ortalama_periyodu=20,
            patlama_esigi=1.50,
        )

        destek_direnc = destek_direnc_bul(
            veri=fiyat_verisi,
            bakis_periyodu=120,
            pivot_genisligi=2,
            birlestirme_toleransi_yuzde=1.00,
        )

        gerekli_sutunlar = [
            "Close",
            "Volume",
            "EMA9",
            "EMA21",
            "RSI14",
            "MACD",
            "MACD_Sinyal",
            "MACD_Histogram",
            "ATR14",
            "ATR_Yuzde",
            "Hacim_Orani",
            "Fiyat_Hacim_Durumu",
        ]

        gecerli_veri = analiz.dropna(
            subset=gerekli_sutunlar
        )

        if len(gecerli_veri) < 2:
            raise StockAnalyzerError(
                f"{sembol} analiz edilemedi: "
                "Analiz için yeterli geçerli veri bulunamadı."
            )

        son = gecerli_veri.iloc[-1]

        giris_fiyati = float(
            son["Close"]
        )

        atr = float(
            son["ATR14"]
        )

        if destek_direnc.direnc is not None:
            risk_plani = yapisal_risk_plani_olustur(
                giris_fiyati=giris_fiyati,
                atr=atr,
                hedef_fiyati=float(
                    destek_direnc.direnc.fiyat
                ),
                stop_atr_katsayisi=1.50,
                minimum_risk_odul=2.00,
            )

            hedef_kaynagi = "Yakın direnç"

        else:
            risk_plani = risk_plani_olustur(
                giris_fiyati=giris_fiyati,
                atr=atr,
                stop_atr_katsayisi=1.50,
                hedef_atr_katsayisi=3.00,
                minimum_risk_odul=2.00,
            )

            hedef_kaynagi = (
                "ATR tahmini — direnç bulunamadı"
            )

        sinyal = sinyal_uret(
            veri=gecerli_veri,
            risk_plani=risk_plani,
        )

        return StockAnalysisResult(
            sembol=sembol,
            analiz_tarihi=str(
                gecerli_veri.index[-1].date()
            ),
            kapanis=float(
                son["Close"]
            ),
            hacim=int(
                son["Volume"]
            ),
            ema9=float(
                son["EMA9"]
            ),
            ema21=float(
                son["EMA21"]
            ),
            rsi14=float(
                son["RSI14"]
            ),
            macd=float(
                son["MACD"]
            ),
            macd_sinyal=float(
                son["MACD_Sinyal"]
            ),
            macd_histogram=float(
                son["MACD_Histogram"]
            ),
            atr14=float(
                son["ATR14"]
            ),
            atr_yuzde=float(
                son["ATR_Yuzde"]
            ),
            hacim_orani=float(
                son["Hacim_Orani"]
            ),
            hacim_durumu=str(
                son["Fiyat_Hacim_Durumu"]
            ),
            destek_direnc=destek_direnc,
            hedef_kaynagi=hedef_kaynagi,
            risk_plani=risk_plani,
            sinyal=sinyal,
        )

    @staticmethod
    def _sembolu_temizle(
        sembol: str,
    ) -> str:
        temiz_sembol = sembol.strip().upper()

        if not temiz_sembol:
            raise ValueError(
                "Hisse sembolü boş olamaz."
            )

        return temiz_sembol