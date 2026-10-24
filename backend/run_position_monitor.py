from __future__ import annotations

import argparse

if __package__:
    from backend.app.analysis.position_monitor import (
        OpenPosition,
        PositionMonitoringResult,
        PositionMonitorError,
        acik_pozisyonu_izle,
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
    from app.analysis.position_monitor import (
        OpenPosition,
        PositionMonitoringResult,
        PositionMonitorError,
        acik_pozisyonu_izle,
    )
    from app.analysis.technical_confirmation import (
        TechnicalConfirmationError,
        teknik_teyit_analizi_yap,
    )
    from app.data.multi_timeframe_data import (
        MultiTimeframeDataError,
        coklu_zaman_dilimi_verisi_getir,
    )


SATIR_GENISLIGI = 118


def argumanlari_oku() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bir BIST hissesindeki açık uzun pozisyonu tamamlanmış mumlar, "
            "dinamik stop, hedef ilerlemesi ve çoklu zaman dilimi teknik "
            "teyidiyle izler."
        )
    )
    parser.add_argument("sembol", help="BIST sembolü. Örnek: THYAO")
    parser.add_argument("--giris", type=float, required=True, help="Giriş fiyatı")
    parser.add_argument("--lot", type=int, required=True, help="Açık lot sayısı")
    parser.add_argument("--stop", type=float, required=True, help="İlk stop fiyatı")
    parser.add_argument("--hedef1", type=float, required=True, help="Birinci hedef")
    parser.add_argument("--hedef2", type=float, required=True, help="İkinci hedef")
    parser.add_argument(
        "--giris-tarihi",
        required=True,
        help="Pozisyon giriş tarihi. Örnek: 2026-07-01",
    )
    parser.add_argument(
        "--mevcut-stop",
        type=float,
        default=None,
        help="Daha önce yükseltilmiş güncel stop seviyesi",
    )
    parser.add_argument(
        "--hedef1-gerceklesti",
        action="store_true",
        help="Birinci hedefte daha önce kısmi kâr alındığını belirtir",
    )
    return parser.parse_args()


def _fiyat(deger: float) -> str:
    return f"{deger:,.2f}"


def _alan_satiri(etiket: str, deger: object) -> str:
    return f"{etiket:<25}: {deger}"


def rapor_metni_olustur(sonuc: PositionMonitoringResult) -> str:
    """Pozisyon raporunu sabit hizalı ve kesintisiz satır sonlarıyla üretir."""
    satirlar = [
        "=" * SATIR_GENISLIGI,
        "HİSSE ROBOTU — AÇIK POZİSYON İZLEME VE DİNAMİK ÇIKIŞ RAPORU",
        "=" * SATIR_GENISLIGI,
        _alan_satiri("Sembol", sonuc.sembol),
        _alan_satiri("Veri kimliği", sonuc.veri_kimligi),
        _alan_satiri("Teknik analiz kimliği", sonuc.teknik_analiz_kimligi),
        _alan_satiri("İzleme kimliği", sonuc.izleme_kimligi),
        _alan_satiri("Pozisyon durumu", sonuc.durum),
        _alan_satiri("Önerilen eylem", sonuc.eylem),
        _alan_satiri("Son tamamlanmış mum", sonuc.son_tarih),
        "",
        "POZİSYON ÖZETİ",
        "-" * SATIR_GENISLIGI,
        _alan_satiri("Giriş tarihi", sonuc.giris_tarihi.date()),
        _alan_satiri("Giriş fiyatı", _fiyat(sonuc.giris_fiyati)),
        _alan_satiri("Son kapanış", _fiyat(sonuc.son_kapanis)),
        _alan_satiri("Açık lot", sonuc.lot_sayisi),
        _alan_satiri("Açık kâr/zarar", _fiyat(sonuc.acik_kar_zarar)),
        _alan_satiri(
            "Açık kâr/zarar yüzdesi",
            f"%{sonuc.acik_kar_zarar_yuzde:.2f}",
        ),
        _alan_satiri("Gerçekleşmemiş R", f"{sonuc.r_katsayisi:.2f}R"),
        _alan_satiri("Pozisyon içi zirve", _fiyat(sonuc.en_yuksek_fiyat)),
        _alan_satiri(
            "En yüksek kapanış",
            _fiyat(sonuc.en_yuksek_kapanis),
        ),
        _alan_satiri("ATR14", _fiyat(sonuc.atr14)),
        "",
        "STOP VE KÂR KORUMA",
        "-" * SATIR_GENISLIGI,
        _alan_satiri("İlk stop", _fiyat(sonuc.ilk_stop)),
        _alan_satiri("Önceki stop", _fiyat(sonuc.onceki_stop)),
        _alan_satiri("Dinamik stop", _fiyat(sonuc.dinamik_stop)),
        _alan_satiri("Stop kaynağı", sonuc.stop_kaynagi),
        _alan_satiri(
            "Stop mesafesi",
            f"{_fiyat(sonuc.stop_mesafesi)} "
            f"(%{sonuc.stop_mesafesi_yuzde:.2f})",
        ),
        "",
        "HEDEF İLERLEMESİ",
        "-" * SATIR_GENISLIGI,
        _alan_satiri(
            "Hedef 1",
            f"{_fiyat(sonuc.hedef_1.hedef)} — {sonuc.hedef_1.durum} "
            f"— kalan %{sonuc.hedef_1.kalan_yuzde:.2f}",
        ),
        _alan_satiri(
            "Hedef 2",
            f"{_fiyat(sonuc.hedef_2.hedef)} — {sonuc.hedef_2.durum} "
            f"— kalan %{sonuc.hedef_2.kalan_yuzde:.2f}",
        ),
        _alan_satiri(
            "Kâr alma değerlendirmesi",
            (
                "Tam çıkış"
                if sonuc.hedef_2.durum == "Ulaşıldı"
                else (
                    f"{sonuc.onerilen_kismi_kar_lotu} lot kısmi kâr"
                    if sonuc.kismi_kar_onerisi
                    else "Yok"
                )
            ),
        ),
        "",
        "POZİTİF UNSURLAR",
    ]

    if sonuc.pozitif_nedenler:
        satirlar.extend(f"  + {neden}" for neden in sonuc.pozitif_nedenler)
    else:
        satirlar.append("  + Belirgin pozitif unsur yok.")

    satirlar.extend(("", "RİSKLER"))
    if sonuc.riskler:
        satirlar.extend(f"  - {risk}" for risk in sonuc.riskler)
    else:
        satirlar.append("  - Belirgin yeni risk yok.")

    satirlar.extend(("", "NOTLAR"))
    if sonuc.notlar:
        satirlar.extend(f"  - {not_metni}" for not_metni in sonuc.notlar)
    else:
        satirlar.append("  - Ek not yok.")

    satirlar.extend(
        (
            "=" * SATIR_GENISLIGI,
            "Not: Dinamik stop yalnızca yukarı taşınır; hedefler pozisyon "
            "dönemindeki tamamlanmış günlük mumların gün içi en yüksek "
            "fiyatlarıyla izlenir. Bu çıktı kişisel analiz amaçlıdır, "
            "yatırım tavsiyesi değildir.",
        )
    )
    return "\n".join(satirlar)


def main() -> int:
    argumanlar = argumanlari_oku()
    sembol = argumanlar.sembol.upper()
    print(f"{sembol} açık pozisyonu güncel verilerle izleniyor...")

    try:
        paket = coklu_zaman_dilimi_verisi_getir(sembol)
        teknik_teyit = teknik_teyit_analizi_yap(paket)
        sonuc = acik_pozisyonu_izle(
            paket=paket,
            teknik_teyit=teknik_teyit,
            pozisyon=OpenPosition(
                giris_tarihi=argumanlar.giris_tarihi,
                giris_fiyati=argumanlar.giris,
                lot_sayisi=argumanlar.lot,
                ilk_stop=argumanlar.stop,
                hedef_1=argumanlar.hedef1,
                hedef_2=argumanlar.hedef2,
                mevcut_stop=argumanlar.mevcut_stop,
                hedef_1_gerceklesti=argumanlar.hedef1_gerceklesti,
            ),
        )
    except (
        MultiTimeframeDataError,
        TechnicalConfirmationError,
        PositionMonitorError,
        ValueError,
    ) as hata:
        print(f"\nHATA: {hata}")
        return 1

    print("\n" + rapor_metni_olustur(sonuc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
