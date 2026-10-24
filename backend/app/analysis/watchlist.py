from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class WatchlistError(Exception):
    """İzleme listesi okunurken oluşan özel hata."""


@dataclass(frozen=True)
class Watchlist:
    """Dosyadan yüklenen kişisel izleme listesini temsil eder."""

    kaynak: str
    semboller: tuple[str, ...]

    @property
    def sembol_sayisi(self) -> int:
        return len(self.semboller)


def izleme_listesi_yukle(
    dosya_yolu: str | Path,
) -> Watchlist:
    """
    Metin dosyasındaki hisse sembollerini yükler.

    Desteklenen ayırıcılar:
        - Yeni satır
        - Boşluk
        - Virgül
        - Noktalı virgül

    '#' işaretinden sonraki metin açıklama kabul edilir.
    """
    yol = Path(dosya_yolu).expanduser()

    if not yol.exists():
        raise WatchlistError(
            f"İzleme listesi dosyası bulunamadı: {yol}"
        )

    if not yol.is_file():
        raise WatchlistError(
            f"İzleme listesi yolu bir dosya değil: {yol}"
        )

    try:
        metin = yol.read_text(
            encoding="utf-8-sig"
        )
    except OSError as hata:
        raise WatchlistError(
            f"İzleme listesi okunamadı: {hata}"
        ) from hata

    semboller = _sembolleri_ayristir(
        metin
    )

    if not semboller:
        raise WatchlistError(
            "İzleme listesinde geçerli hisse sembolü bulunamadı."
        )

    return Watchlist(
        kaynak=str(yol),
        semboller=tuple(semboller),
    )


def _sembolleri_ayristir(
    metin: str,
) -> list[str]:
    """
    Dosya içeriğini temizler, büyük harfe çevirir
    ve yinelenen sembolleri kaldırır.
    """
    temiz_satirlar: list[str] = []

    for satir in metin.splitlines():
        yorumdan_once = satir.split(
            "#",
            maxsplit=1,
        )[0].strip()

        if yorumdan_once:
            temiz_satirlar.append(
                yorumdan_once
            )

    birlesik_metin = "\n".join(
        temiz_satirlar
    )

    parcalar = re.split(
        r"[\s,;]+",
        birlesik_metin,
    )

    semboller: list[str] = []
    gorulenler: set[str] = set()

    for parca in parcalar:
        sembol = parca.lstrip("\ufeff").strip().upper()

        if not sembol:
            continue

        if not re.fullmatch(
            r"[A-Z0-9.-]+",
            sembol,
        ):
            raise WatchlistError(
                f"Geçersiz hisse sembolü: {sembol}"
            )

        if sembol in gorulenler:
            continue

        gorulenler.add(sembol)
        semboller.append(sembol)

    return semboller