from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen


RESMI_BIST_BILESEN_URL = (
    "https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv"
)

EVREN_KODLARI = {
    "BIST 30": "XU030",
    "BIST 100": "XU100",
    "BIST 500": "XU500",
    "BIST Tüm": "XUTUM",
}


class BistUniverseError(Exception):
    """BIST endeks bileşenleri yüklenemediğinde oluşturulur."""


@dataclass(frozen=True)
class BistUniverse:
    """Bir BIST tarama evreninin sembollerini ve veri kaynağını temsil eder."""

    ad: str
    endeks_kodu: str
    semboller: tuple[str, ...]
    tarih: str
    kaynak: str
    resmi_kaynaktan_guncel: bool

    @property
    def sembol_sayisi(self) -> int:
        return len(self.semboller)


Downloader = Callable[[str], bytes]


class BistUniverseRepository:
    """
    Borsa İstanbul'un güncel endeks bileşenleri CSV'sini indirir.

    Ağ erişimi başarısız olursa önce son başarılı yerel önbelleği, ardından
    projeyle birlikte gelen resmi veri anlık görüntüsünü kullanır.
    """

    def __init__(
        self,
        snapshot_yolu: str | Path | None = None,
        onbellek_yolu: str | Path | None = None,
        indirici: Downloader | None = None,
    ) -> None:
        backend = Path(__file__).resolve().parents[2]
        self._snapshot_yolu = Path(snapshot_yolu) if snapshot_yolu else (
            backend / "resources" / "bist_endeks_bilesenleri.csv"
        )
        self._onbellek_yolu = Path(onbellek_yolu) if onbellek_yolu else (
            backend / "cache" / "bist_endeks_bilesenleri.csv"
        )
        self._indirici = indirici or _resmi_csv_indir

    def evreni_yukle(
        self,
        evren_adi: str,
        internetten_guncelle: bool = True,
    ) -> BistUniverse:
        if evren_adi not in EVREN_KODLARI:
            raise ValueError(
                f"Bilinmeyen BIST evreni: {evren_adi}. "
                f"Geçerli seçenekler: {', '.join(EVREN_KODLARI)}"
            )

        endeks_kodu = EVREN_KODLARI[evren_adi]
        hatalar: list[str] = []

        if internetten_guncelle:
            try:
                veri = self._indirici(RESMI_BIST_BILESEN_URL)
                evren = bist_bilesen_csvsini_ayristir(
                    veri,
                    evren_adi=evren_adi,
                    endeks_kodu=endeks_kodu,
                    kaynak="Borsa İstanbul güncel CSV",
                    resmi_kaynaktan_guncel=True,
                )
                self._onbellegi_yaz(veri)
                return evren
            except (OSError, URLError, ValueError, BistUniverseError) as hata:
                hatalar.append(f"Güncel kaynak: {hata}")

        for yol, kaynak in (
            (self._onbellek_yolu, "Yerel BIST önbelleği"),
            (self._snapshot_yolu, "Paketlenmiş BIST anlık görüntüsü"),
        ):
            try:
                veri = yol.read_bytes()
                return bist_bilesen_csvsini_ayristir(
                    veri,
                    evren_adi=evren_adi,
                    endeks_kodu=endeks_kodu,
                    kaynak=kaynak,
                    resmi_kaynaktan_guncel=False,
                )
            except (OSError, ValueError, BistUniverseError) as hata:
                hatalar.append(f"{kaynak}: {hata}")

        raise BistUniverseError(
            "BIST evreni yüklenemedi. " + " | ".join(hatalar)
        )

    def _onbellegi_yaz(self, veri: bytes) -> None:
        try:
            self._onbellek_yolu.parent.mkdir(parents=True, exist_ok=True)
            self._onbellek_yolu.write_bytes(veri)
        except OSError:
            # Önbellek yazma hatası güncel verinin kullanımını engellememelidir.
            return


def bist_bilesen_csvsini_ayristir(
    veri: bytes | str,
    evren_adi: str,
    endeks_kodu: str,
    kaynak: str,
    resmi_kaynaktan_guncel: bool,
) -> BistUniverse:
    """Borsa İstanbul'un noktalı virgüllü bileşen CSV'sini ayrıştırır."""
    metin = veri.decode("utf-8-sig") if isinstance(veri, bytes) else veri
    satirlar = csv.reader(StringIO(metin), delimiter=";")

    semboller: list[str] = []
    gorulenler: set[str] = set()
    tarihler: set[str] = set()

    for satir in satirlar:
        if len(satir) < 6:
            continue
        if satir[2].strip().upper() != endeks_kodu:
            continue

        bilesen_kodu = satir[0].strip().upper()
        if not bilesen_kodu.endswith(".E"):
            continue

        yahoo_sembolu = f"{bilesen_kodu.removesuffix('.E')}.IS"
        if yahoo_sembolu in gorulenler:
            continue

        gorulenler.add(yahoo_sembolu)
        semboller.append(yahoo_sembolu)

        tarih = satir[5].strip()
        if tarih:
            tarihler.add(tarih)

    if not semboller:
        raise BistUniverseError(
            f"{endeks_kodu} için geçerli hisse bileşeni bulunamadı."
        )

    tarih_metni = ", ".join(sorted(tarihler)) if tarihler else "Bilinmiyor"

    return BistUniverse(
        ad=evren_adi,
        endeks_kodu=endeks_kodu,
        semboller=tuple(semboller),
        tarih=tarih_metni,
        kaynak=kaynak,
        resmi_kaynaktan_guncel=resmi_kaynaktan_guncel,
    )


def _resmi_csv_indir(url: str) -> bytes:
    istek = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 Hisse-Robotu/1.0 "
                "(+personal-research-tool)"
            )
        },
    )
    with urlopen(istek, timeout=30) as yanit:
        return yanit.read()
