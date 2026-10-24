from __future__ import annotations

from datetime import date

from backend.app.data.batch_market_data import toplu_fiyat_verisi_getir


SYMBOLS = [
    "THYAO.IS",
    "ASELS.IS",
    "TUPRS.IS",
    "SAHOL.IS",
    "KCHOL.IS",
    "AKBNK.IS",
    "GARAN.IS",
    "BIMAS.IS",
]


def main() -> int:
    print("SPRINT-144C LIVE BATCH MERGE VALIDATION")
    print("=" * 78)

    result = toplu_fiyat_verisi_getir(
        SYMBOLS,
        islem_gunu=5,
        indirme_donemi="1mo",
        bugun=date(2026, 8, 4),
    )

    print("Kaynak sırası :", result.kaynak_sirasi)
    print("Kaynak hataları:", len(result.kaynak_hatalari))
    for item in result.kaynak_hatalari[:10]:
        print(" -", item)
    print()

    failed = []

    for symbol in SYMBOLS:
        frame = result.veriler.get(symbol)
        if frame is None or frame.empty:
            print(symbol, "YOK")
            failed.append(symbol)
            continue

        row = frame.iloc[-1]
        last = frame.index[-1].date()
        print(
            f"{symbol:10s} SON={last} "
            f"O={row['Open']:.2f} "
            f"H={row['High']:.2f} "
            f"L={row['Low']:.2f} "
            f"C={row['Close']:.2f} "
            f"V={row['Volume']:.0f}"
        )
        if last != date(2026, 8, 3):
            failed.append(symbol)

    print()
    if failed:
        print(
            "SONUC: BASARISIZ — 03.08 ile bitmeyen/eksik semboller:",
            ", ".join(failed),
        )
        return 10

    thyao = result.veriler["THYAO.IS"].iloc[-1]
    expected = (320.5, 322.25, 316.5, 317.0, 46594813.0)
    actual = (
        float(thyao["Open"]),
        float(thyao["High"]),
        float(thyao["Low"]),
        float(thyao["Close"]),
        float(thyao["Volume"]),
    )
    if actual != expected:
        print("SONUC: BASARISIZ — THYAO resmî OHLCV uyuşmuyor:", actual)
        return 11

    print(
        "SONUC: BASARILI — Yahoo tarihsel seri + Borsa Istanbul "
        "resmî son günlük bar tek batch seride birleşti."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
