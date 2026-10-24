from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.analysis.scan_export import (
    ScanExportError,
    tarama_sonucunu_csv_kaydet,
)
from app.analysis.scan_filter import (
    tarama_sonucunu_filtrele,
)
from app.analysis.scan_profiles import (
    profil_adlari,
)
from app.analysis.stock_scanner import (
    StockScanner,
)
from app.analysis.watchlist import (
    WatchlistError,
    izleme_listesi_yukle,
)
from app.history.scan_history import (
    ScanHistoryError,
    ScanHistoryRepository,
)
from run_stock_scanner import (
    filtrelenmis_sonucu_yazdir,
    ilerlemeyi_yazdir,
    kriterleri_olustur,
)


def backend_klasoru() -> Path:
    return Path(__file__).resolve().parent


def varsayilan_liste_yolu() -> Path:
    return (
        backend_klasoru()
        / "watchlists"
        / "favoriler.txt"
    )


def varsayilan_csv_yolu() -> Path:
    simdi = datetime.now(
        ZoneInfo("Europe/Istanbul")
    )

    dosya_adi = (
        "tarama_"
        + simdi.strftime("%Y-%m-%d_%H-%M-%S")
        + ".csv"
    )

    return (
        backend_klasoru()
        / "reports"
        / dosya_adi
    )


def varsayilan_veritabani_yolu() -> Path:
    return (
        backend_klasoru()
        / "database"
        / "scan_history.db"
    )


def argumanlari_al() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Kişisel izleme listesindeki BIST hisselerini "
            "analiz eder, filtreler, CSV olarak kaydeder "
            "ve SQLite geçmişine ekler."
        )
    )

    parser.add_argument(
        "--liste",
        type=Path,
        default=varsayilan_liste_yolu(),
        help=(
            "İzleme listesi dosyasının yolu. "
            "Varsayılan: backend/watchlists/favoriler.txt"
        ),
    )

    parser.add_argument(
        "--profil",
        choices=profil_adlari(),
        default="gevsek",
        help=(
            "Tarama profili: gevsek, dengeli veya siki. "
            "Varsayılan: gevsek"
        ),
    )

    parser.add_argument(
        "--min-skor",
        type=int,
        default=None,
        help="Profildeki minimum skoru değiştirir.",
    )

    parser.add_argument(
        "--min-hacim",
        type=float,
        default=None,
        help="Profildeki minimum hacim oranını değiştirir.",
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
        help="Profildeki teknik görünüm seçimini değiştirir.",
    )

    parser.add_argument(
        "--risk-gecen",
        action="store_true",
        help=(
            "Yalnızca risk/ödül filtresini geçen "
            "hisseleri gösterir."
        ),
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help=(
            "CSV dosyasının kaydedileceği özel yol. "
            "Belirtilmezse tarih-saat içeren dosya oluşturulur."
        ),
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=varsayilan_veritabani_yolu(),
        help=(
            "SQLite veritabanı yolu. "
            "Varsayılan: backend/database/scan_history.db"
        ),
    )

    return parser.parse_args()


def main() -> None:
    argumanlar = argumanlari_al()

    try:
        izleme_listesi = izleme_listesi_yukle(
            argumanlar.liste
        )

        kriterler, profil_metni = (
            kriterleri_olustur(
                argumanlar
            )
        )

        print(
            "\nİzleme listesi: "
            f"{izleme_listesi.kaynak}"
        )

        print(
            "Yüklenen hisse sayısı: "
            f"{izleme_listesi.sembol_sayisi}"
        )

        print(
            f"{profil_metni} profiliyle "
            "tarama başlıyor...\n"
        )

        tarama = StockScanner().tara(
            semboller=izleme_listesi.semboller,
            ilerleme_bildirimi=ilerlemeyi_yazdir,
        )

        filtrelenmis_sonuc = (
            tarama_sonucunu_filtrele(
                tarama=tarama,
                kriterler=kriterler,
            )
        )

        csv_yolu = (
            argumanlar.csv
            if argumanlar.csv is not None
            else varsayilan_csv_yolu()
        )

        disari_aktarma = tarama_sonucunu_csv_kaydet(
            sonuc=filtrelenmis_sonuc,
            dosya_yolu=csv_yolu,
        )

        gecmis_repository = ScanHistoryRepository(
            argumanlar.db
        )

        gecmis_kaydi = (
            gecmis_repository.taramayi_kaydet(
                sonuc=filtrelenmis_sonuc,
                kriterler=kriterler,
                profil_adi=profil_metni,
            )
        )

    except (
        ValueError,
        WatchlistError,
        ScanExportError,
        ScanHistoryError,
    ) as hata:
        print(f"\nHATA: {hata}")
        return

    filtrelenmis_sonucu_yazdir(
        sonuc=filtrelenmis_sonuc,
        kriterler=kriterler,
        profil_metni=profil_metni,
    )

    print()
    print("CSV RAPORU")
    print("-" * 105)
    print(
        "Dosya yolu           : "
        f"{disari_aktarma.dosya_yolu}"
    )
    print(
        "Kaydedilen satır     : "
        f"{disari_aktarma.satir_sayisi}"
    )

    print()
    print("SQLITE TARAMA GEÇMİŞİ")
    print("-" * 105)
    print(
        "Veritabanı yolu      : "
        f"{gecmis_kaydi.veritabani_yolu}"
    )
    print(
        "Tarama kimliği       : "
        f"{gecmis_kaydi.tarama_id}"
    )
    print(
        "Kaydedilen kayıt     : "
        f"{gecmis_kaydi.kaydedilen_kayit_sayisi}"
    )


if __name__ == "__main__":
    main()