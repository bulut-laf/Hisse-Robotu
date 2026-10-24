from __future__ import annotations

import sys

from app.analysis.support_resistance import (
    SupportResistanceError,
    destek_direnc_bul,
)
from app.data.market_data import (
    MarketDataError,
    fiyat_verisi_getir,
)
from app.indicators.technical_indicators import (
    IndicatorError,
    teknik_gostergeleri_ekle,
)
from app.risk.risk_engine import (
    RiskEngineError,
)
from app.risk.structural_risk import (
    yapisal_risk_plani_olustur,
)


def main() -> None:
    sembol = (
        sys.argv[1].strip().upper()
        if len(sys.argv) > 1
        else "ASELS.IS"
    )

    print(
        f"\n{sembol} yapısal risk planı hazırlanıyor...\n"
    )

    try:
        fiyat_verisi = fiyat_verisi_getir(
            sembol=sembol,
            islem_gunu=160,
            indirme_donemi="1y",
            yalnizca_tamamlanmis_gunler=True,
        )

        teknik_veri = teknik_gostergeleri_ekle(
            fiyat_verisi
        )

        gecerli_veri = teknik_veri.dropna(
            subset=[
                "Close",
                "ATR14",
            ]
        )

        if gecerli_veri.empty:
            print(
                "HATA: Geçerli ATR verisi bulunamadı."
            )
            return

        destek_direnc = destek_direnc_bul(
            veri=fiyat_verisi,
            bakis_periyodu=120,
            pivot_genisligi=2,
            birlestirme_toleransi_yuzde=1.00,
        )

        if destek_direnc.direnc is None:
            print(
                "HATA: Yapısal hedef olarak "
                "kullanılabilecek direnç bulunamadı."
            )
            return

        son = gecerli_veri.iloc[-1]

        plan = yapisal_risk_plani_olustur(
            giris_fiyati=float(
                son["Close"]
            ),
            atr=float(
                son["ATR14"]
            ),
            hedef_fiyati=float(
                destek_direnc.direnc.fiyat
            ),
            stop_atr_katsayisi=1.50,
            minimum_risk_odul=2.00,
        )

    except (
        ValueError,
        MarketDataError,
        IndicatorError,
        SupportResistanceError,
        RiskEngineError,
    ) as hata:
        print(f"HATA: {hata}")
        return

    print(f"Giriş fiyatı         : {plan.giris_fiyati:.2f}")

    if destek_direnc.destek is not None:
        print(
            f"Yakın destek         : "
            f"{destek_direnc.destek.fiyat:.2f}"
        )

    print(
        f"Yapısal hedef        : "
        f"{plan.hedef_fiyat:.2f}"
    )
    print(f"ATR tabanlı stop     : {plan.stop_loss:.2f}")
    print(f"Risk tutarı          : {plan.risk_tutari:.2f}")
    print(f"Ödül tutarı          : {plan.odul_tutari:.2f}")
    print(
        f"Gerçek risk/ödül     : "
        f"1:{plan.risk_odul_orani:.2f}"
    )
    print(f"Risk notu            : {plan.risk_notu}")
    print(
        f"Risk/ödül filtresi   : "
        f"{'Geçti' if plan.filtreyi_gecti else 'Elendi'}"
    )


if __name__ == "__main__":
    main()