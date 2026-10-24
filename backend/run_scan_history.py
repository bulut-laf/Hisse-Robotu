from __future__ import annotations

import argparse
from pathlib import Path

from app.history.scan_history import (
    ScanHistoryError,
    ScanHistoryRepository,
)
from app.history.scan_history_reader import (
    ScanHistoryReader,
    ScanItemDetail,
    ScanRunDetail,
)


SATIR_GENISLIGI = 120


def backend_klasoru() -> Path:
    return Path(__file__).resolve().parent


def varsayilan_veritabani_yolu() -> Path:
    return (
        backend_klasoru()
        / "database"
        / "scan_history.db"
    )


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "SQLite veritabanında saklanan hisse "
            "taramalarını listeler veya seçilen "
            "bir taramanın ayrıntılarını gösterir."
        )
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=varsayilan_veritabani_yolu(),
        help=(
            "SQLite veritabanının yolu. "
            "Varsayılan: backend/database/scan_history.db"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help=(
            "Listeleme görünümünde gösterilecek "
            "tarama sayısı. Varsayılan: 10"
        ),
    )

    parser.add_argument(
        "--id",
        type=int,
        default=None,
        dest="tarama_id",
        help=(
            "Ayrıntıları gösterilecek taramanın kimliği."
        ),
    )

    return parser.parse_args()


def tarama_gecmisini_yazdir(
    repository: ScanHistoryRepository,
    limit: int,
) -> None:
    taramalar = repository.son_taramalari_getir(
        limit=limit
    )

    print()
    print("=" * SATIR_GENISLIGI)
    print("HİSSE ROBOTU — TARAMA GEÇMİŞİ")
    print("=" * SATIR_GENISLIGI)

    print(
        "Veritabanı: "
        f"{repository.veritabani_yolu}"
    )

    print(
        "Gösterilen tarama sayısı: "
        f"{len(taramalar)}"
    )

    if not taramalar:
        print()
        print(
            "Henüz kayıtlı tarama bulunmuyor."
        )
        print("=" * SATIR_GENISLIGI)
        return

    print()
    print(
        f"{'ID':<6}"
        f"{'Tarih':<32}"
        f"{'Profil':<20}"
        f"{'Toplam':>12}"
        f"{'Aday':>12}"
        f"{'Elendi':>12}"
        f"{'Hata':>12}"
    )

    print("-" * SATIR_GENISLIGI)

    for tarama in taramalar:
        print(
            f"{tarama.tarama_id:<6}"
            f"{tarama.olusturma_zamani:<32}"
            f"{tarama.profil_adi:<20}"
            f"{tarama.toplam_sayi:>12}"
            f"{tarama.aday_sayisi:>12}"
            f"{tarama.elenen_sayisi:>12}"
            f"{tarama.hatali_sayisi:>12}"
        )

    print("=" * SATIR_GENISLIGI)

    print()
    print(
        "Bir taramanın ayrıntıları için:"
    )
    print(
        "python backend\\run_scan_history.py --id TARAMA_ID"
    )


def tarama_detayini_yazdir(
    detay: ScanRunDetail,
    veritabani_yolu: str,
) -> None:
    ozet = detay.ozet

    print()
    print("=" * SATIR_GENISLIGI)
    print(
        "HİSSE ROBOTU — TARAMA AYRINTILARI"
    )
    print("=" * SATIR_GENISLIGI)

    print(
        f"Veritabanı            : {veritabani_yolu}"
    )
    print(
        f"Tarama kimliği        : {ozet.tarama_id}"
    )
    print(
        f"Tarama zamanı         : {ozet.olusturma_zamani}"
    )
    print(
        f"Tarama profili        : {ozet.profil_adi}"
    )

    print()
    print("UYGULANAN FİLTRELER")
    print("-" * SATIR_GENISLIGI)

    print(
        f"Minimum skor          : {ozet.minimum_skor}"
    )
    print(
        "Minimum hacim oranı   : "
        f"{ozet.minimum_hacim_orani:.2f}x"
    )
    print(
        "Risk/ödül şartı       : "
        + (
            "Gerekli"
            if ozet.risk_odul_gerekli
            else "Gerekli değil"
        )
    )
    print(
        "Teknik görünüm        : "
        + ", ".join(
            ozet.izin_verilen_gorunumler
        )
    )

    print()
    print("TARAMA ÖZETİ")
    print("-" * SATIR_GENISLIGI)

    print(
        f"Toplam                : {ozet.toplam_sayi}"
    )
    print(
        f"Aday                  : {ozet.aday_sayisi}"
    )
    print(
        f"Elendi                : {ozet.elenen_sayisi}"
    )
    print(
        f"Hatalı                : {ozet.hatali_sayisi}"
    )

    adaylar = tuple(
        kayit
        for kayit in detay.kayitlar
        if kayit.durum == "Aday"
    )

    elenenler = tuple(
        kayit
        for kayit in detay.kayitlar
        if kayit.durum == "Elendi"
    )

    hatalar = tuple(
        kayit
        for kayit in detay.kayitlar
        if kayit.durum == "Hata"
    )

    _adaylari_yazdir(
        adaylar
    )

    _elenenleri_yazdir(
        elenenler
    )

    _hatalari_yazdir(
        hatalar
    )

    print()
    print("=" * SATIR_GENISLIGI)


def _adaylari_yazdir(
    adaylar: tuple[ScanItemDetail, ...],
) -> None:
    print()
    print("ADAY HİSSELER")
    print("-" * SATIR_GENISLIGI)

    if not adaylar:
        print("Aday hisse bulunmuyor.")
        return

    _tablo_basligini_yazdir()

    for kayit in adaylar:
        _hisse_satirini_yazdir(
            kayit
        )


def _elenenleri_yazdir(
    elenenler: tuple[ScanItemDetail, ...],
) -> None:
    print()
    print("ELENEN HİSSELER")
    print("-" * SATIR_GENISLIGI)

    if not elenenler:
        print("Elenen hisse bulunmuyor.")
        return

    _tablo_basligini_yazdir()

    for kayit in elenenler:
        _hisse_satirini_yazdir(
            kayit
        )

        if kayit.aciklama:
            print(
                f"     Neden: {kayit.aciklama}"
            )


def _hatalari_yazdir(
    hatalar: tuple[ScanItemDetail, ...],
) -> None:
    print()
    print("HATALI KAYITLAR")
    print("-" * SATIR_GENISLIGI)

    if not hatalar:
        print("Hatalı kayıt bulunmuyor.")
        return

    for kayit in hatalar:
        print(
            f"- {kayit.sembol}: {kayit.aciklama}"
        )


def _tablo_basligini_yazdir() -> None:
    print(
        f"{'Sıra':<5}  "
        f"{'Sembol':<12}  "
        f"{'Skor':>5}  "
        f"{'Görünüm':<8}  "
        f"{'Kapanış':>10}  "
        f"{'RSI':>7}  "
        f"{'Hacim':>8}  "
        f"{'R/R':>7}  "
        f"{'Hedef':>10}  "
        f"{'Filtre':>8}"
    )

    print("-" * SATIR_GENISLIGI)


def _hisse_satirini_yazdir(
    kayit: ScanItemDetail,
) -> None:
    sira = (
        str(kayit.sira)
        if kayit.sira is not None
        else "-"
    )

    skor = (
        str(kayit.skor)
        if kayit.skor is not None
        else "-"
    )

    gorunum = _gorunum_kisalt(
        kayit.teknik_gorunum
    )

    kapanis = _ondalik_deger(
        kayit.kapanis
    )

    rsi = _ondalik_deger(
        kayit.rsi14
    )

    hacim = (
        f"{kayit.hacim_orani:.2f}x"
        if kayit.hacim_orani is not None
        else "-"
    )

    risk_odul = _ondalik_deger(
        kayit.risk_odul_orani
    )

    hedef = _ondalik_deger(
        kayit.hedef_fiyat
    )

    risk_filtresi = _risk_filtresi_metni(
        kayit.risk_filtresi_gecti
    )

    print(
        f"{sira:<5}  "
        f"{kayit.sembol:<12}  "
        f"{skor:>5}  "
        f"{gorunum:<8}  "
        f"{kapanis:>10}  "
        f"{rsi:>7}  "
        f"{hacim:>8}  "
        f"{risk_odul:>7}  "
        f"{hedef:>10}  "
        f"{risk_filtresi:>8}"
    )

def _ondalik_deger(
    deger: float | None,
) -> str:
    if deger is None:
        return "-"

    return f"{deger:.2f}"


def _gorunum_kisalt(
    gorunum: str | None,
) -> str:
    if gorunum is None:
        return "-"

    donusumler = {
        "Pozitif Teknik Görünüm": "Pozitif",
        "Nötr Teknik Görünüm": "Nötr",
        "Negatif Teknik Görünüm": "Negatif",
    }

    return donusumler.get(
        gorunum,
        gorunum,
    )


def _risk_filtresi_metni(
    deger: bool | None,
) -> str:
    if deger is None:
        return "-"

    return (
        "Geçti"
        if deger
        else "Elendi"
    )


def main() -> None:
    argumanlar = argumanlari_al()

    try:
        if argumanlar.tarama_id is None:
            repository = ScanHistoryRepository(
                argumanlar.db
            )

            tarama_gecmisini_yazdir(
                repository=repository,
                limit=argumanlar.limit,
            )

        else:
            reader = ScanHistoryReader(
                argumanlar.db
            )

            detay = reader.tarama_detayini_getir(
                tarama_id=argumanlar.tarama_id
            )

            tarama_detayini_yazdir(
                detay=detay,
                veritabani_yolu=(
                    reader.veritabani_yolu
                ),
            )

    except (
        ValueError,
        ScanHistoryError,
    ) as hata:
        print(f"\nHATA: {hata}")


if __name__ == "__main__":
    main()