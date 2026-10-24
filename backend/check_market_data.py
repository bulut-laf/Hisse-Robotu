from app.data.market_data import MarketDataError, fiyat_verisi_getir


def main() -> None:
    sembol = "THYAO.IS"

    print(f"\n{sembol} verisi indiriliyor...\n")

    try:
        veri = fiyat_verisi_getir(
            sembol=sembol,
            islem_gunu=60,
        )
    except (ValueError, MarketDataError) as hata:
        print(f"HATA: {hata}")
        return

    print(f"Toplam işlem günü : {len(veri)}")
    print(f"İlk tarih          : {veri.index.min().date()}")
    print(f"Son tarih          : {veri.index.max().date()}")

    print("\nSon 5 işlem günü:\n")
    print(veri.tail(5).round(2))


if __name__ == "__main__":
    main()