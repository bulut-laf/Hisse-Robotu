from __future__ import annotations

import argparse

if __package__:
    from backend.app.analysis.trade_plan import (
        TradePlanError,
        islem_plani_olustur,
    )
    from backend.app.analysis.technical_confirmation import (
        TechnicalConfirmationError,
        teknik_teyit_analizi_yap,
    )
    from backend.app.data.multi_timeframe_data import (
        MultiTimeframeDataError,
        coklu_zaman_dilimi_verisi_getir,
    )
else:
    from app.analysis.trade_plan import (
        TradePlanError,
        islem_plani_olustur,
    )
    from app.analysis.technical_confirmation import (
        TechnicalConfirmationError,
        teknik_teyit_analizi_yap,
    )
    from app.data.multi_timeframe_data import (
        MultiTimeframeDataError,
        coklu_zaman_dilimi_verisi_getir,
    )


SATIR_GENISLIGI = 112


def argumanlari_oku() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bir BIST hissesi için çoklu zaman dilimi teyidine dayalı "
            "güncel alış, stop, hedef ve pozisyon büyüklüğü planı üretir."
        )
    )
    parser.add_argument("sembol", help="BIST sembolü. Örnek: THYAO")
    parser.add_argument(
        "--sermaye",
        type=float,
        default=100_000.0,
        help="Hesaplamada kullanılacak sermaye. Varsayılan: 100000",
    )
    parser.add_argument(
        "--risk-yuzde",
        type=float,
        default=1.0,
        help="İşlem başına azami sermaye riski yüzdesi. Varsayılan: 1",
    )
    return parser.parse_args()


def _fiyat(deger: float | None) -> str:
    return "Yok" if deger is None else f"{deger:,.2f}"


def _oran(deger: float | None) -> str:
    return "Yok" if deger is None else f"1:{deger:.2f}"


def main() -> int:
    argumanlar = argumanlari_oku()
    sembol = argumanlar.sembol.upper()

    print(f"{sembol} için güncel alış-satış işlem planı hazırlanıyor...")

    try:
        paket = coklu_zaman_dilimi_verisi_getir(sembol)
        teknik_teyit = teknik_teyit_analizi_yap(paket)
        plan = islem_plani_olustur(
            paket=paket,
            teknik_teyit=teknik_teyit,
            sermaye=argumanlar.sermaye,
            azami_risk_orani=argumanlar.risk_yuzde / 100.0,
        )
    except (
        MultiTimeframeDataError,
        TechnicalConfirmationError,
        TradePlanError,
        ValueError,
    ) as hata:
        print(f"\nHATA: {hata}")
        return 1

    print("\n" + "=" * SATIR_GENISLIGI)
    print("HİSSE ROBOTU — GÜNCEL ALIŞ-SATIŞ İŞLEM PLANI")
    print("=" * SATIR_GENISLIGI)
    print(f"Sembol                 : {plan.sembol}")
    print(f"Veri kimliği           : {plan.veri_kimligi}")
    print(f"Teknik analiz kimliği  : {plan.teknik_analiz_kimligi}")
    print(f"Plan kimliği           : {plan.plan_kimligi}")
    print(f"Teknik teyit skoru     : {plan.teyit_skoru}/100")
    print(f"Karar                  : {plan.karar}")
    print(f"Plan tipi              : {plan.plan_tipi}")
    print(f"Son kapanış            : {_fiyat(plan.son_kapanis)}")
    print(f"ATR14                   : {_fiyat(plan.atr14)} (%{plan.atr_yuzde:.2f})")
    print(f"İzleme tetik seviyesi  : {_fiyat(plan.izleme_tetik_fiyati)}")

    if plan.giris_alt is not None:
        print("\nİŞLEM SEVİYELERİ")
        print("-" * SATIR_GENISLIGI)
        print(
            f"Giriş bölgesi           : {_fiyat(plan.giris_alt)} — "
            f"{_fiyat(plan.giris_ust)}"
        )
        print(f"Referans giriş          : {_fiyat(plan.referans_giris)}")
        print(f"Stop-loss               : {_fiyat(plan.stop_loss)}")
        print(f"Hedef 1                 : {_fiyat(plan.hedef_1)}")
        print(f"Hedef 2                 : {_fiyat(plan.hedef_2)}")
        print(f"Risk/ödül Hedef 1       : {_oran(plan.risk_odul_1)}")
        print(f"Risk/ödül Hedef 2       : {_oran(plan.risk_odul_2)}")
        print(f"Giriş kaynağı           : {plan.giris_kaynagi}")
        print(f"Stop kaynağı            : {plan.stop_kaynagi}")
        print(f"Hedef 1 kaynağı         : {plan.hedef_1_kaynagi}")
        print(f"Hedef 2 kaynağı         : {plan.hedef_2_kaynagi}")

    if plan.pozisyon is not None:
        pozisyon = plan.pozisyon
        print("\nPOZİSYON BÜYÜKLÜĞÜ")
        print("-" * SATIR_GENISLIGI)
        print(f"Sermaye                 : {pozisyon.sermaye:,.2f}")
        print(f"Risk bütçesi            : {pozisyon.risk_butcesi:,.2f}")
        print(f"Lot sayısı              : {pozisyon.lot_sayisi}")
        print(f"Pozisyon tutarı         : {pozisyon.pozisyon_tutari:,.2f}")
        print(f"Planlanan azami risk    : {pozisyon.planlanan_risk:,.2f}")
        print(
            f"Sermaye kullanımı       : "
            f"%{pozisyon.sermaye_kullanim_orani * 100:.2f}"
        )

    print("\nBEKLENEN TEYİTLER")
    if plan.beklenen_teyitler:
        for teyit in plan.beklenen_teyitler:
            print(f"  - {teyit}")
    else:
        print("  - Ek teyit beklenmiyor.")

    print("\nPLANI GEÇERSİZ KILAN KOŞULLAR")
    for kosul in plan.gecersizlik_kosullari:
        print(f"  - {kosul}")

    print("\nNOTLAR")
    for not_metni in plan.notlar:
        print(f"  - {not_metni}")

    print("=" * SATIR_GENISLIGI)
    print(
        "Not: İşlem Var kararı yalnızca tamamlanmış mum teyidi ve risk "
        "filtreleri geçildiğinde üretilir. Bu çıktı kişisel analiz "
        "amaçlıdır, yatırım tavsiyesi değildir."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
