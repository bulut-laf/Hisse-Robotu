from __future__ import annotations

import math

from .risk_engine import (
    RiskEngineError,
    RiskPlan,
    volatilite_notu_belirle,
)


def yapisal_risk_plani_olustur(
    giris_fiyati: float,
    atr: float,
    hedef_fiyati: float,
    stop_atr_katsayisi: float = 1.50,
    minimum_risk_odul: float = 2.00,
) -> RiskPlan:
    """
    ATR tabanlı stop ve fiyat yapısından gelen gerçek hedef
    kullanarak risk planı oluşturur.

    Hedef fiyat genellikle en yakın direnç seviyesidir.
    """
    if giris_fiyati <= 0:
        raise ValueError(
            "Giriş fiyatı pozitif olmalıdır."
        )

    if atr <= 0:
        raise ValueError(
            "ATR pozitif olmalıdır."
        )

    if hedef_fiyati <= 0:
        raise ValueError(
            "Hedef fiyat pozitif olmalıdır."
        )

    if stop_atr_katsayisi <= 0:
        raise ValueError(
            "Stop ATR katsayısı pozitif olmalıdır."
        )

    if minimum_risk_odul <= 0:
        raise ValueError(
            "Minimum risk/ödül oranı pozitif olmalıdır."
        )

    if hedef_fiyati <= giris_fiyati:
        raise RiskEngineError(
            "Yapısal hedef fiyatı giriş fiyatının "
            "üzerinde olmalıdır."
        )

    stop_loss = (
        giris_fiyati
        - (atr * stop_atr_katsayisi)
    )

    if stop_loss <= 0:
        raise RiskEngineError(
            "Hesaplanan stop-loss sıfırın altında "
            "veya sıfıra eşit."
        )

    risk_tutari = giris_fiyati - stop_loss
    odul_tutari = hedef_fiyati - giris_fiyati

    if risk_tutari <= 0:
        raise RiskEngineError(
            "Risk tutarı pozitif olmalıdır."
        )

    risk_odul_orani = (
        odul_tutari / risk_tutari
    )

    atr_yuzde = (
        atr / giris_fiyati
    ) * 100

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
        hedef_fiyat=float(hedef_fiyati),
        risk_tutari=float(risk_tutari),
        odul_tutari=float(odul_tutari),
        risk_odul_orani=float(
            risk_odul_orani
        ),
        atr=float(atr),
        atr_yuzde=float(atr_yuzde),
        risk_notu=volatilite_notu_belirle(
            atr_yuzde
        ),
        minimum_risk_odul=float(
            minimum_risk_odul
        ),
        filtreyi_gecti=filtreyi_gecti,
    )