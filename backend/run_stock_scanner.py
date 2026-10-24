from __future__ import annotations

import argparse
import re

from app.analysis.scan_filter import (
    NEGATIF_GORUNUM,
    NOTR_GORUNUM,
    POZITIF_GORUNUM,
    TUM_GORUNUMLER,
    FilteredScanResult,
    ScanFilterCriteria,
    tarama_sonucunu_filtrele,
)
from app.analysis.scan_profiles import (
    profil_adlari,
    profil_al,
)
from app.analysis.stock_scanner import StockScanner


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Birden fazla BIST hissesini analiz eder, "
            "filtreler ve skora göre sıralar."
        )
    )

    parser.add_argument(
        "semboller",
        nargs="*",
        help="Hisse kodları. Örnek: THYAO ASELS TUPRS",
    )

    parser.add_argument(
        "--profil",
        choices=profil_adlari(),
        default=None,
        help=(
            "Hazır tarama profili: "
            "gevsek, dengeli veya siki"
        ),
    )

    parser.add_argument(
        "--min-skor",
        type=int,
        default=None,
        help=(
            "Profildeki minimum skoru değiştirir. "
            "Örnek: --min-skor 60"
        ),
    )

    parser.add_argument(
        "--min-hacim",
        type=float,
        default=None,
        help=(
            "Profildeki minimum hacim oranını değiştirir. "
            "Örnek: --min-hacim 1.20"
        ),
    )

    parser.add_argument(
        "--gorunum",
        choices=[
            "tum",
            "pozitif",
            "notr",
            "negatif",
            "pozitif-notr",
        ],
        default=None,
        help=(
            "Profildeki teknik görünüm seçimini değiştirir."
        ),
    )

    parser.add_argument(
        "--risk-gecen",
        action="store_true",
        help=(
            "Yalnızca risk/ödül filtresini geçen "
            "hisseleri gösterir."
        ),
    )

    return parser.parse_args()


def sembolleri_al(
    terminal_sembolleri: list[str],
) -> list[str]:
    if terminal_sembolleri:
        ham_degerler = terminal_sembolleri
    else:
        kullanici_girdisi = input(
            "Taranacak hisseleri girin "
            "(örnek: THYAO, ASELS, TUPRS): "
        )

        ham_degerler = [
            kullanici_girdisi
        ]

    semboller: list[str] = []

    for ham_deger in ham_degerler:
        parcalar = re.split(
            r"[\s,;]+",
            ham_deger.strip(),
        )

        semboller.extend(
            parca
            for parca in parcalar
            if parca
        )

    return semboller


def ilerlemeyi_yazdir(
    sira: int,
    toplam: int,
    sembol: str,
) -> None:
    print(
        f"[{sira}/{toplam}] "
        f"{sembol} analiz ediliyor..."
    )


def izin_verilen_gorunumleri_belirle(
    gorunum_secimi: str,
) -> tuple[str, ...]:
    eslestirme = {
        "tum": TUM_GORUNUMLER,
        "pozitif": (
            POZITIF_GORUNUM,
        ),
        "notr": (
            NOTR_GORUNUM,
        ),
        "negatif": (
            NEGATIF_GORUNUM,
        ),
        "pozitif-notr": (
            POZITIF_GORUNUM,
            NOTR_GORUNUM,
        ),
    }

    return eslestirme[
        gorunum_secimi
    ]


def kriterleri_olustur(
    argumanlar: argparse.Namespace,
) -> tuple[ScanFilterCriteria, str]:
    """
    Hazır profili temel alır.

    Terminalden ayrıca verilen seçenekler profil değerlerinin
    üzerine yazılır.
    """
    if argumanlar.profil is not None:
        profil = profil_al(
            argumanlar.profil
        )

        temel_kriterler = profil.kriterler
        profil_metni = profil.ad

    else:
        temel_kriterler = ScanFilterCriteria()
        profil_metni = "Özel / profilsiz"

    minimum_skor = (
        argumanlar.min_skor
        if argumanlar.min_skor is not None
        else temel_kriterler.minimum_skor
    )

    minimum_hacim_orani = (
        argumanlar.min_hacim
        if argumanlar.min_hacim is not None
        else temel_kriterler.minimum_hacim_orani
    )

    if argumanlar.gorunum is not None:
        izin_verilen_gorunumler = (
            izin_verilen_gorunumleri_belirle(
                argumanlar.gorunum
            )
        )
    else:
        izin_verilen_gorunumler = (
            temel_kriterler.izin_verilen_gorunumler
        )

    risk_odul_filtresi_gerekli = (
        argumanlar.risk_gecen
        or temel_kriterler.risk_odul_filtresi_gerekli
    )

    kriterler = ScanFilterCriteria(
        minimum_skor=minimum_skor,
        minimum_hacim_orani=minimum_hacim_orani,
        risk_odul_filtresi_gerekli=(
            risk_odul_filtresi_gerekli
        ),
        izin_verilen_gorunumler=(
            izin_verilen_gorunumler
        ),
    )

    return kriterler, profil_metni


def gorunumu_kisalt(
    karar: str,
) -> str:
    if karar == POZITIF_GORUNUM:
        return "Pozitif"

    if karar == NOTR_GORUNUM:
        return "Nötr"

    return "Negatif"


def filtrelenmis_sonucu_yazdir(
    sonuc: FilteredScanResult,
    kriterler: ScanFilterCriteria,
    profil_metni: str,
) -> None:
    ayirici = "=" * 105

    risk_sarti = (
        "Gerekli"
        if kriterler.risk_odul_filtresi_gerekli
        else "Gerekli değil"
    )

    gorunum_metni = ", ".join(
        kriterler.izin_verilen_gorunumler
    )

    print()
    print(ayirici)
    print(
        "HİSSE ROBOTU — "
        "FİLTRELENMİŞ TARAMA SONUÇLARI"
    )
    print(ayirici)

    print(
        f"Toplam: {sonuc.toplam_sayisi} | "
        f"Aday: {sonuc.aday_sayisi} | "
        f"Elenen: {sonuc.elenen_sayisi} | "
        f"Hatalı: {sonuc.hatali_sayisi}"
    )

    print()
    print("UYGULANAN FİLTRELER")
    print("-" * 105)
    print(f"Tarama profili       : {profil_metni}")
    print(
        f"Minimum skor         : "
        f"{kriterler.minimum_skor}"
    )
    print(
        f"Minimum hacim oranı  : "
        f"{kriterler.minimum_hacim_orani:.2f}x"
    )
    print(f"Risk/ödül şartı      : {risk_sarti}")
    print(f"Teknik görünüm       : {gorunum_metni}")

    print()
    print("ADAY HİSSELER")
    print("-" * 105)

    if not sonuc.adaylar:
        print(
            "Filtre koşullarını karşılayan "
            "hisse bulunamadı."
        )

    else:
        print(
            "{:<5}{:<13}{:>7}{:>12}{:>12}{:>8}"
            "{:>10}{:>8}{:>12}{:>10}".format(
                "Sıra",
                "Sembol",
                "Skor",
                "Görünüm",
                "Kapanış",
                "RSI",
                "Hacim",
                "R/R",
                "Hedef",
                "Filtre",
            )
        )

        print("-" * 105)

        for sira, hisse in enumerate(
            sonuc.adaylar,
            start=1,
        ):
            risk_filtresi = (
                "Geçti"
                if hisse.risk_plani.filtreyi_gecti
                else "Elendi"
            )

            gorunum = gorunumu_kisalt(
                hisse.sinyal.karar
            )

            print(
                "{:<5}{:<13}{:>7}{:>12}{:>12.2f}{:>8.2f}"
                "{:>9.2f}x{:>8.2f}{:>12.2f}{:>10}".format(
                    sira,
                    hisse.sembol,
                    hisse.sinyal.skor,
                    gorunum,
                    hisse.kapanis,
                    hisse.rsi14,
                    hisse.hacim_orani,
                    hisse.risk_plani.risk_odul_orani,
                    hisse.risk_plani.hedef_fiyat,
                    risk_filtresi,
                )
            )

    if sonuc.elenenler:
        print()
        print("ELENEN HİSSELER")
        print("-" * 105)

        for elenen in sonuc.elenenler:
            print()
            print(f"- {elenen.sembol}")

            for neden in elenen.nedenler:
                print(f"  • {neden}")

    if sonuc.hatalar:
        print()
        print("ANALİZ EDİLEMEYEN HİSSELER")
        print("-" * 105)

        for hata in sonuc.hatalar:
            print(
                f"- {hata.sembol}: {hata.hata}"
            )

    print()
    print(ayirici)
    print(
        "Bu tarama kişisel araştırma amaçlıdır."
    )
    print(ayirici)


def main() -> None:
    argumanlar = argumanlari_al()

    semboller = sembolleri_al(
        argumanlar.semboller
    )

    if not semboller:
        print(
            "HATA: En az bir hisse kodu girilmelidir."
        )
        return

    try:
        kriterler, profil_metni = (
            kriterleri_olustur(
                argumanlar
            )
        )

        print(
            f"\n{len(semboller)} hisse için "
            f"{profil_metni.lower()} tarama başlıyor...\n"
        )

        tarama = StockScanner().tara(
            semboller=semboller,
            ilerleme_bildirimi=(
                ilerlemeyi_yazdir
            ),
        )

        filtrelenmis_sonuc = (
            tarama_sonucunu_filtrele(
                tarama=tarama,
                kriterler=kriterler,
            )
        )

    except ValueError as hata:
        print(f"HATA: {hata}")
        return

    filtrelenmis_sonucu_yazdir(
        sonuc=filtrelenmis_sonuc,
        kriterler=kriterler,
        profil_metni=profil_metni,
    )


if __name__ == "__main__":
    main()