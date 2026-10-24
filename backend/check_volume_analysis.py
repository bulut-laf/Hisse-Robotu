from app.analysis.volume_analysis import (
    VolumeAnalysisError,
    hacim_gostergelerini_ekle,
    son_hacim_ozeti,
)
from app.data.market_data import (
    MarketDataError,
    fiyat_verisi_getir,
)


def main() -> None:
    sembol = "THYAO.IS"

    print(f"\n{sembol} hacim analizi hazırlanıyor...\n")

    try:
        fiyat_verisi = fiyat_verisi_getir(
            sembol=sembol,
            islem_gunu=60,
        )

        analiz = hacim_gostergelerini_ekle(
            veri=fiyat_verisi,
            ortalama_periyodu=20,
            patlama_esigi=1.50,
        )

        ozet = son_hacim_ozeti(
            veri=analiz,
            ortalama_periyodu=20,
        )

    except (
        ValueError,
        MarketDataError,
        VolumeAnalysisError,
    ) as hata:
        print(f"HATA: {hata}")
        return

    print(f"Analiz tarihi       : {analiz.index[-1].date()}")
    print(f"Güncel hacim        : {ozet['hacim']:,}")
    print(
        f"20 günlük ortalama  : "
        f"{ozet['ortalama_hacim']:,}"
    )
    print(f"Hacim oranı         : {ozet['hacim_orani']:.2f}x")
    print(
        f"Günlük getiri       : "
        f"%{ozet['gunluk_getiri_yuzde']:.2f}"
    )
    print(
        f"Hacim patlaması     : "
        f"{'Evet' if ozet['hacim_patlamasi'] else 'Hayır'}"
    )
    print(f"Fiyat-hacim durumu  : {ozet['durum']}")

    print("\nSon 5 işlem günü:\n")

    gosterilecek_sutunlar = [
        "Close",
        "Volume",
        "Ortalama_Hacim_20",
        "Hacim_Orani",
        "Gunluk_Getiri_Yuzde",
        "Hacim_Patlamasi",
        "Fiyat_Hacim_Durumu",
    ]

    print(
        analiz[
            gosterilecek_sutunlar
        ].tail(5).round(2)
    )


if __name__ == "__main__":
    main()