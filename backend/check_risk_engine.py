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
    risk_plani_olustur,
)


def main() -> None:
    sembol = "THYAO.IS"

    print(f"\n{sembol} risk analizi hazırlanıyor...\n")

    try:
        fiyat_verisi = fiyat_verisi_getir(
            sembol=sembol,
            islem_gunu=120,
        )

        teknik_analiz = teknik_gostergeleri_ekle(
            fiyat_verisi
        )

        gecerli_veri = teknik_analiz.dropna(
            subset=[
                "Close",
                "ATR14",
            ]
        )

        if gecerli_veri.empty:
            print(
                "HATA: Risk planı için geçerli ATR verisi bulunamadı."
            )
            return

        son = gecerli_veri.iloc[-1]

        risk_plani = risk_plani_olustur(
            giris_fiyati=float(son["Close"]),
            atr=float(son["ATR14"]),
            stop_atr_katsayisi=1.50,
            hedef_atr_katsayisi=3.00,
            minimum_risk_odul=2.00,
        )

    except (
        ValueError,
        MarketDataError,
        IndicatorError,
        RiskEngineError,
    ) as hata:
        print(f"HATA: {hata}")
        return

    print(f"Analiz tarihi      : {gecerli_veri.index[-1].date()}")
    print(f"Giriş fiyatı       : {risk_plani.giris_fiyati:.2f}")
    print(f"ATR 14             : {risk_plani.atr:.2f}")
    print(f"ATR yüzde          : %{risk_plani.atr_yuzde:.2f}")
    print(f"Stop-loss          : {risk_plani.stop_loss:.2f}")
    print(f"Hedef fiyat        : {risk_plani.hedef_fiyat:.2f}")
    print(f"Risk tutarı        : {risk_plani.risk_tutari:.2f}")
    print(f"Ödül tutarı        : {risk_plani.odul_tutari:.2f}")
    print(
        f"Risk/ödül oranı    : "
        f"1:{risk_plani.risk_odul_orani:.2f}"
    )
    print(f"Risk notu          : {risk_plani.risk_notu}")
    print(
        f"RR filtresi        : "
        f"{'Geçti' if risk_plani.filtreyi_gecti else 'Elendi'}"
    )


if __name__ == "__main__":
    main()