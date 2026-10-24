from app.analysis.signal_engine import (
    SignalEngineError,
    sinyal_uret,
)
from app.analysis.volume_analysis import (
    VolumeAnalysisError,
    hacim_gostergelerini_ekle,
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
    risk_plani_olustur,
)


def main() -> None:
    sembol = "THYAO.IS"

    print(f"\n{sembol} sinyal analizi hazırlanıyor...\n")

    try:
        fiyat_verisi = fiyat_verisi_getir(
            sembol=sembol,
            islem_gunu=120,
        )

        analiz = teknik_gostergeleri_ekle(
            fiyat_verisi
        )

        analiz = hacim_gostergelerini_ekle(
            analiz
        )

        gecerli_veri = analiz.dropna(
            subset=[
                "Close",
                "EMA9",
                "EMA21",
                "RSI14",
                "MACD",
                "MACD_Sinyal",
                "MACD_Histogram",
                "ATR14",
                "Hacim_Orani",
            ]
        )

        if gecerli_veri.empty:
            print(
                "HATA: Sinyal üretmek için geçerli veri bulunamadı."
            )
            return

        son = gecerli_veri.iloc[-1]

        risk_plani = risk_plani_olustur(
            giris_fiyati=float(son["Close"]),
            atr=float(son["ATR14"]),
        )

        sinyal = sinyal_uret(
            veri=gecerli_veri,
            risk_plani=risk_plani,
        )

    except (
        ValueError,
        MarketDataError,
        IndicatorError,
        VolumeAnalysisError,
        RiskEngineError,
        SignalEngineError,
    ) as hata:
        print(f"HATA: {hata}")
        return

    print(f"Analiz tarihi       : {gecerli_veri.index[-1].date()}")
    print(f"Kapanış             : {son['Close']:.2f}")
    print(f"Sinyal skoru        : {sinyal.skor}/100")
    print(f"Karar               : {sinyal.karar}")

    print("\nPuan dağılımı:")
    print(f"Trend               : {sinyal.trend_puani}/30")
    print(f"Momentum            : {sinyal.momentum_puani}/30")
    print(f"Hacim               : {sinyal.hacim_puani}/20")
    print(f"Risk                : {sinyal.risk_puani}/20")

    print("\nRisk planı:")
    print(f"Giriş               : {risk_plani.giris_fiyati:.2f}")
    print(f"Stop-loss           : {risk_plani.stop_loss:.2f}")
    print(f"Hedef               : {risk_plani.hedef_fiyat:.2f}")
    print(
        f"Risk/ödül           : "
        f"1:{risk_plani.risk_odul_orani:.2f}"
    )
    print(f"Risk notu           : {risk_plani.risk_notu}")

    print("\nPozitif nedenler:")

    if sinyal.pozitif_nedenler:
        for neden in sinyal.pozitif_nedenler:
            print(f"  + {neden}")
    else:
        print("  Pozitif teknik neden bulunamadı.")

    print("\nRiskler:")

    if sinyal.riskler:
        for risk in sinyal.riskler:
            print(f"  - {risk}")
    else:
        print("  Belirgin teknik risk bulunamadı.")


if __name__ == "__main__":
    main()