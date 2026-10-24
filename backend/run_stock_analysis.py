from __future__ import annotations

import argparse

from app.analysis.stock_analyzer import (
    StockAnalysisResult,
    StockAnalyzer,
    StockAnalyzerError,
)


def argumanlari_al() -> argparse.Namespace:
    """
    Terminalden isteğe bağlı hisse kodu alır.

    Örnek:
        python backend/run_stock_analysis.py THYAO.IS
    """
    parser = argparse.ArgumentParser(
        description=(
            "Tek bir hisse için kısa vadeli teknik "
            "analiz ve risk raporu üretir."
        )
    )

    parser.add_argument(
        "sembol",
        nargs="?",
        help="Hisse kodu. Örnek: THYAO.IS veya AAPL",
    )

    return parser.parse_args()


def sembol_al(
    terminal_sembolu: str | None,
) -> str:
    """
    Komut satırında sembol verilmediyse kullanıcıdan ister.
    """
    if terminal_sembolu:
        return terminal_sembolu.strip().upper()

    return input(
        "Analiz edilecek hisse kodunu girin "
        "(örnek: THYAO.IS): "
    ).strip().upper()


def sonucu_yazdir(
    sonuc: StockAnalysisResult,
) -> None:
    """
    Bütünleşik analiz sonucunu okunabilir biçimde gösterir.
    """
    sinyal = sonuc.sinyal
    risk = sonuc.risk_plani

    ayirici = "=" * 62

    print(f"\n{ayirici}")
    print("HİSSE ROBOTU — KISA VADELİ ANALİZ RAPORU")
    print(ayirici)

    print(f"Hisse                 : {sonuc.sembol}")
    print(f"Analiz tarihi         : {sonuc.analiz_tarihi}")
    print(f"Kapanış               : {sonuc.kapanis:.2f}")
    print(f"Sinyal skoru          : {sinyal.skor}/100")
    print(f"Teknik görünüm        : {sinyal.karar}")

    print("\nPUAN DAĞILIMI")
    print("-" * 62)
    print(f"Trend                 : {sinyal.trend_puani}/30")
    print(f"Momentum              : {sinyal.momentum_puani}/30")
    print(f"Hacim                 : {sinyal.hacim_puani}/20")
    print(f"Risk                  : {sinyal.risk_puani}/20")

    print("\nTEKNİK GÖSTERGELER")
    print("-" * 62)
    print(f"EMA 9                 : {sonuc.ema9:.2f}")
    print(f"EMA 21                : {sonuc.ema21:.2f}")
    print(f"RSI 14                : {sonuc.rsi14:.2f}")
    print(f"MACD                  : {sonuc.macd:.4f}")
    print(f"MACD sinyal           : {sonuc.macd_sinyal:.4f}")
    print(f"MACD histogram        : {sonuc.macd_histogram:.4f}")
    print(f"ATR 14                : {sonuc.atr14:.2f}")
    print(f"ATR yüzde             : %{sonuc.atr_yuzde:.2f}")

    print("\nHACİM ANALİZİ")
    print("-" * 62)
    print(f"Güncel hacim          : {sonuc.hacim:,}")
    print(f"Hacim oranı           : {sonuc.hacim_orani:.2f}x")
    print(f"Hacim durumu          : {sonuc.hacim_durumu}")
    destek_direnc = sonuc.destek_direnc

    print("\nDESTEK / DİRENÇ")
    print("-" * 62)

    if destek_direnc.destek is not None:
        print(
            f"Yakın destek          : "
            f"{destek_direnc.destek.fiyat:.2f}"
        )
        print(
            f"Destek uzaklığı       : "
            f"%{destek_direnc.destek_uzaklik_yuzde:.2f}"
        )
        print(
            f"Destek gücü           : "
            f"{destek_direnc.destek.guc}"
        )
    else:
        print("Yakın destek          : Bulunamadı")

    if destek_direnc.direnc is not None:
        print(
            f"Yakın direnç          : "
            f"{destek_direnc.direnc.fiyat:.2f}"
        )
        print(
            f"Direnç uzaklığı       : "
            f"%{destek_direnc.direnc_uzaklik_yuzde:.2f}"
        )
        print(
            f"Direnç gücü           : "
            f"{destek_direnc.direnc.guc}"
        )
    else:
        print("Yakın direnç          : Bulunamadı")
    print("\nRİSK PLANI")
    print("-" * 62)
    print(f"Giriş fiyatı          : {risk.giris_fiyati:.2f}")
    print(f"Stop-loss             : {risk.stop_loss:.2f}")
    print(f"Hedef fiyat           : {risk.hedef_fiyat:.2f}")
    print(f"Hedef kaynağı         : {sonuc.hedef_kaynagi}")
    print(f"Risk tutarı           : {risk.risk_tutari:.2f}")
    print(f"Ödül tutarı           : {risk.odul_tutari:.2f}")
    print(f"Risk/ödül             : 1:{risk.risk_odul_orani:.2f}")
    print(f"Risk notu             : {risk.risk_notu}")
    print(
        f"Risk/ödül filtresi    : "
        f"{'Geçti' if risk.filtreyi_gecti else 'Elendi'}"
    )

    print("\nPOZİTİF NEDENLER")
    print("-" * 62)

    if sinyal.pozitif_nedenler:
        for neden in sinyal.pozitif_nedenler:
            print(f"+ {neden}")
    else:
        print("Pozitif teknik neden bulunamadı.")

    print("\nRİSKLER")
    print("-" * 62)

    if sinyal.riskler:
        for risk_nedeni in sinyal.riskler:
            print(f"- {risk_nedeni}")
    else:
        print("Belirgin teknik risk bulunamadı.")

    print(f"\n{ayirici}")
    print("Bu rapor kişisel araştırma amaçlıdır.")
    print(ayirici)


def main() -> None:
    argumanlar = argumanlari_al()
    sembol = sembol_al(argumanlar.sembol)

    if not sembol:
        print("HATA: Hisse kodu boş bırakılamaz.")
        return

    print(f"\n{sembol} analiz ediliyor...")

    try:
        sonuc = StockAnalyzer().analiz_et(sembol)

    except (
        ValueError,
        StockAnalyzerError,
    ) as hata:
        print(f"\nHATA: {hata}")
        return

    sonucu_yazdir(sonuc)


if __name__ == "__main__":
    main()