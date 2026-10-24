from __future__ import annotations

from dataclasses import dataclass
import math


class RiskEngineError(Exception):
    """Risk planı oluşturulamadığında meydana gelen özel hata."""


@dataclass(frozen=True)
class RiskPlan:
    """
    Tek bir uzun pozisyon için oluşturulan risk planı.

    Fiyatlar hesaplama hassasiyetini korumak için yuvarlanmadan
    saklanır. Kullanıcıya gösterilirken yuvarlanabilir.
    """

    giris_fiyati: float
    stop_loss: float
    hedef_fiyat: float
    risk_tutari: float
    odul_tutari: float
    risk_odul_orani: float
    atr: float
    atr_yuzde: float
    risk_notu: str
    minimum_risk_odul: float
    filtreyi_gecti: bool


def risk_plani_olustur(
    giris_fiyati: float,
    atr: float,
    stop_atr_katsayisi: float = 1.50,
    hedef_atr_katsayisi: float = 3.00,
    minimum_risk_odul: float = 2.00,
) -> RiskPlan:
    """
    ATR tabanlı uzun pozisyon risk planı oluşturur.

    Varsayılan hesaplama:
        Stop mesafesi  = 1,50 ATR
        Hedef mesafesi = 3,00 ATR

    Bu katsayılarla teorik risk/ödül oranı:
        3,00 / 1,50 = 2,00

    Parametreler:
        giris_fiyati:
            Planlanan işlem giriş fiyatı.

        atr:
            Hissenin ATR değeri.

        stop_atr_katsayisi:
            Stop-loss mesafesinin kaç ATR olacağı.

        hedef_atr_katsayisi:
            Hedef mesafesinin kaç ATR olacağı.

        minimum_risk_odul:
            Fırsatın kabul edilmesi için gereken en düşük
            risk/ödül oranı.
    """
    _girdileri_dogrula(
        giris_fiyati=giris_fiyati,
        atr=atr,
        stop_atr_katsayisi=stop_atr_katsayisi,
        hedef_atr_katsayisi=hedef_atr_katsayisi,
        minimum_risk_odul=minimum_risk_odul,
    )

    stop_mesafesi = atr * stop_atr_katsayisi
    hedef_mesafesi = atr * hedef_atr_katsayisi

    stop_loss = giris_fiyati - stop_mesafesi
    hedef_fiyat = giris_fiyati + hedef_mesafesi

    if stop_loss <= 0:
        raise RiskEngineError(
            "Hesaplanan stop-loss sıfır veya negatif oldu. "
            "ATR veya stop katsayısı bu fiyat için çok yüksek."
        )

    risk_tutari = giris_fiyati - stop_loss
    odul_tutari = hedef_fiyat - giris_fiyati

    if risk_tutari <= 0:
        raise RiskEngineError(
            "Risk tutarı sıfırdan büyük olmalıdır."
        )

    risk_odul_orani = odul_tutari / risk_tutari

    atr_yuzde = atr / giris_fiyati * 100
    risk_notu = volatilite_notu_belirle(atr_yuzde)

    filtreyi_gecti = (
    risk_odul_orani > minimum_risk_odul
    or math.isclose(
        risk_odul_orani,
        minimum_risk_odul,
        rel_tol=1e-9,
        abs_tol=1e-9,
    )
)

    return RiskPlan(
        giris_fiyati=float(giris_fiyati),
        stop_loss=float(stop_loss),
        hedef_fiyat=float(hedef_fiyat),
        risk_tutari=float(risk_tutari),
        odul_tutari=float(odul_tutari),
        risk_odul_orani=float(risk_odul_orani),
        atr=float(atr),
        atr_yuzde=float(atr_yuzde),
        risk_notu=risk_notu,
        minimum_risk_odul=float(minimum_risk_odul),
        filtreyi_gecti=filtreyi_gecti,
    )


def volatilite_notu_belirle(
    atr_yuzde: float,
) -> str:
    """
    ATR'nin giriş fiyatına oranına göre volatilite sınıfı üretir.

    Sınıflandırma:
        %2 altı      : Düşük Volatiliteli
        %2 - %4      : Orta Volatiliteli
        %4 üzeri     : Yüksek Volatiliteli
    """
    if atr_yuzde < 0:
        raise ValueError(
            "ATR yüzdesi negatif olamaz."
        )

    if atr_yuzde < 2.0:
        return "Düşük Volatiliteli"

    if atr_yuzde <= 4.0:
        return "Orta Volatiliteli"

    return "Yüksek Volatiliteli"


def _girdileri_dogrula(
    giris_fiyati: float,
    atr: float,
    stop_atr_katsayisi: float,
    hedef_atr_katsayisi: float,
    minimum_risk_odul: float,
) -> None:
    """Risk motoruna verilen sayısal girdileri doğrular."""
    if giris_fiyati <= 0:
        raise ValueError(
            "Giriş fiyatı sıfırdan büyük olmalıdır."
        )

    if atr <= 0:
        raise ValueError(
            "ATR değeri sıfırdan büyük olmalıdır."
        )

    if stop_atr_katsayisi <= 0:
        raise ValueError(
            "Stop ATR katsayısı sıfırdan büyük olmalıdır."
        )

    if hedef_atr_katsayisi <= 0:
        raise ValueError(
            "Hedef ATR katsayısı sıfırdan büyük olmalıdır."
        )

    if minimum_risk_odul <= 0:
        raise ValueError(
            "Minimum risk/ödül oranı sıfırdan büyük olmalıdır."
        )