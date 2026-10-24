from app.analysis.stock_analyzer import (
    StockAnalyzer,
    StockAnalyzerError,
)


def main() -> None:
    sembol = "THYAO.IS"
    analiz_motoru = StockAnalyzer()

    print(f"\n{sembol} bütünleşik analizi hazırlanıyor...\n")

    try:
        sonuc = analiz_motoru.analiz_et(sembol)
    except (
        ValueError,
        StockAnalyzerError,
    ) as hata:
        print(f"HATA: {hata}")
        return

    print(f"Hisse               : {sonuc.sembol}")
    print(f"Analiz tarihi       : {sonuc.analiz_tarihi}")
    print(f"Kapanış             : {sonuc.kapanis:.2f}")
    print(f"Sinyal skoru        : {sonuc.sinyal.skor}/100")
    print(f"Karar               : {sonuc.sinyal.karar}")

    print("\nTeknik göstergeler:")
    print(f"EMA 9               : {sonuc.ema9:.2f}")
    print(f"EMA 21              : {sonuc.ema21:.2f}")
    print(f"RSI 14              : {sonuc.rsi14:.2f}")
    print(f"MACD                : {sonuc.macd:.4f}")
    print(f"MACD sinyal         : {sonuc.macd_sinyal:.4f}")
    print(f"ATR yüzde           : %{sonuc.atr_yuzde:.2f}")

    print("\nHacim:")
    print(f"Güncel hacim        : {sonuc.hacim:,}")
    print(f"Hacim oranı         : {sonuc.hacim_orani:.2f}x")
    print(f"Hacim durumu        : {sonuc.hacim_durumu}")

    print("\nRisk planı:")
    print(
        f"Giriş               : "
        f"{sonuc.risk_plani.giris_fiyati:.2f}"
    )
    print(
        f"Stop-loss           : "
        f"{sonuc.risk_plani.stop_loss:.2f}"
    )
    print(
        f"Hedef               : "
        f"{sonuc.risk_plani.hedef_fiyat:.2f}"
    )
    print(
        f"Risk/ödül           : "
        f"1:{sonuc.risk_plani.risk_odul_orani:.2f}"
    )
    print(
        f"Risk notu           : "
        f"{sonuc.risk_plani.risk_notu}"
    )

    print("\nPuan dağılımı:")
    print(
        f"Trend               : "
        f"{sonuc.sinyal.trend_puani}/30"
    )
    print(
        f"Momentum            : "
        f"{sonuc.sinyal.momentum_puani}/30"
    )
    print(
        f"Hacim               : "
        f"{sonuc.sinyal.hacim_puani}/20"
    )
    print(
        f"Risk                : "
        f"{sonuc.sinyal.risk_puani}/20"
    )


if __name__ == "__main__":
    main()