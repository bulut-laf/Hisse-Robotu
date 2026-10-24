from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

if __package__ in (None, ""):
    PROJE_KOKU = Path(__file__).resolve().parents[1]
    if str(PROJE_KOKU) not in sys.path:
        sys.path.insert(0, str(PROJE_KOKU))

from backend.app.diagnostics.system_check import (  # noqa: E402
    BASARILI,
    BASARISIZ,
    UYARI,
    SystemCheckReport,
    sistem_kontrolu_calistir,
)


DURUM_SIMGE = {
    BASARILI: "[OK]",
    UYARI: "[UYARI]",
    BASARISIZ: "[HATA]",
}


def argumanlari_oku() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Hisse Robotu çalışma ortamını ve ana iş akışlarını ağ bağlantısı "
            "kullanmadan doğrular."
        )
    )
    parser.add_argument(
        "--proje-koku",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Kontrol edilecek proje klasörü.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Sonucu okunabilir metin yerine JSON olarak yazdırır.",
    )
    return parser.parse_args()


def rapor_metni_olustur(rapor: SystemCheckReport) -> str:
    satirlar = [
        "=" * 104,
        "HİSSE ROBOTU — SİSTEM KONTROLÜ VE UÇTAN UCA DOĞRULAMA",
        "=" * 104,
        f"Sürüm              : {rapor.surum}",
        f"Kullanıma hazır    : {'Evet' if rapor.kullanima_hazir else 'Hayır'}",
        f"Başarılı / Uyarı / Hata: {rapor.basarili_sayisi} / "
        f"{rapor.uyari_sayisi} / {rapor.basarisiz_sayisi}",
        "-" * 104,
    ]
    for item in rapor.kontroller:
        satirlar.append(
            f"{DURUM_SIMGE[item.durum]:<8} {item.ad:<36} "
            f"{item.sure_ms:>8.2f} ms  {item.aciklama}"
        )
    satirlar.extend(
        (
            "=" * 104,
            (
                "SONUÇ: Sistem kullanıma hazır."
                if rapor.kullanima_hazir
                else "SONUÇ: Kritik hatalar giderilmeden programı kullanmayın."
            ),
        )
    )
    return os.linesep.join(satirlar)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = argumanlari_oku()
    rapor = sistem_kontrolu_calistir(proje_koku=args.proje_koku)
    print(rapor.json_metni() if args.json else rapor_metni_olustur(rapor))
    return 0 if rapor.kullanima_hazir else 1


if __name__ == "__main__":
    raise SystemExit(main())
