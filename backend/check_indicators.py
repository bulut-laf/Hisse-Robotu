from app.data.market_data import (
    MarketDataError,
    fiyat_verisi_getir,
)
from app.indicators.technical_indicators import (
    IndicatorError,
    teknik_gostergeleri_ekle,
)


def main() -> None:
    sembol = "THYAO.IS"

    print(f"\n{sembol} teknik analizi hazırlanıyor...\n")

    try:
        # Göstergelerin başlangıç değerlerinin daha sağlıklı olması
        # için 120 işlem günü kullanıyoruz.
        fiyat_verisi = fiyat_verisi_getir(
            sembol=sembol,
            islem_gunu=120,
        )

        analiz = teknik_gostergeleri_ekle(fiyat_verisi)

    except (
        ValueError,
        MarketDataError,
        IndicatorError,
    ) as hata:
        print(f"HATA: {hata}")
        return

    gecerli_analiz = analiz.dropna(
        subset=[
            "EMA9",
            "EMA21",
            "RSI14",
            "MACD",
            "MACD_Sinyal",
            "ATR14",
        ]
    )

    if gecerli_analiz.empty:
        print("HATA: Geçerli teknik gösterge üretilemedi.")
        return

    son = gecerli_analiz.iloc[-1]

    print(f"Analiz tarihi : {gecerli_analiz.index[-1].date()}")
    print(f"Kapanış       : {son['Close']:.2f}")
    print(f"EMA 9         : {son['EMA9']:.2f}")
    print(f"EMA 21        : {son['EMA21']:.2f}")
    print(f"RSI 14        : {son['RSI14']:.2f}")
    print(f"MACD          : {son['MACD']:.4f}")
    print(f"MACD sinyal   : {son['MACD_Sinyal']:.4f}")
    print(f"MACD histogram: {son['MACD_Histogram']:.4f}")
    print(f"ATR 14        : {son['ATR14']:.2f}")
    print(f"ATR yüzde     : %{son['ATR_Yuzde']:.2f}")

    print("\nSon 5 işlem günü:\n")

    gosterilecek_sutunlar = [
        "Close",
        "EMA9",
        "EMA21",
        "RSI14",
        "MACD",
        "MACD_Sinyal",
        "ATR14",
        "ATR_Yuzde",
    ]

    print(
        gecerli_analiz[
            gosterilecek_sutunlar
        ].tail(5).round(2)
    )


if __name__ == "__main__":
    main()