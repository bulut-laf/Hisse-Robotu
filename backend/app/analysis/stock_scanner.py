from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from ..data.batch_market_data import (
    BatchMarketDataResult,
    toplu_fiyat_verisi_getir,
)
from .stock_analyzer import (
    StockAnalysisResult,
    StockAnalyzer,
    StockAnalyzerError,
)


@dataclass(frozen=True)
class ScanFailure:
    """Analiz edilemeyen bir hisseyi temsil eder."""

    sembol: str
    hata: str


@dataclass(frozen=True)
class StockScanResult:
    """Çoklu hisse taramasının bütün sonucunu temsil eder."""

    basarili_sonuclar: tuple[StockAnalysisResult, ...]
    hatalar: tuple[ScanFailure, ...]

    @property
    def toplam_sembol(self) -> int:
        return len(self.basarili_sonuclar) + len(self.hatalar)

    @property
    def basarili_sayisi(self) -> int:
        return len(self.basarili_sonuclar)

    @property
    def hatali_sayisi(self) -> int:
        return len(self.hatalar)

    @property
    def pozitif_sayisi(self) -> int:
        return sum(
            sonuc.sinyal.karar == "Pozitif Teknik Görünüm"
            for sonuc in self.basarili_sonuclar
        )

    @property
    def notr_sayisi(self) -> int:
        return sum(
            sonuc.sinyal.karar == "Nötr Teknik Görünüm"
            for sonuc in self.basarili_sonuclar
        )

    @property
    def negatif_sayisi(self) -> int:
        return sum(
            sonuc.sinyal.karar == "Negatif Teknik Görünüm"
            for sonuc in self.basarili_sonuclar
        )


class StockScanner:
    """
    Birden fazla hisseyi analiz eder ve sonuçları
    sinyal skoruna göre sıralar.
    """

    def __init__(
        self,
        analiz_motoru: StockAnalyzer | None = None,
    ) -> None:
        self._analiz_motoru = (
            analiz_motoru
            if analiz_motoru is not None
            else StockAnalyzer()
        )

    def tara(
        self,
        semboller: Iterable[str],
        ilerleme_bildirimi: (
            Callable[[int, int, str], None] | None
        ) = None,
    ) -> StockScanResult:
        """
        Verilen sembolleri sırayla analiz eder.

        Nokta içermeyen sembollere BIST için otomatik olarak
        '.IS' uzantısı eklenir.
        """
        temiz_semboller = _sembolleri_hazirla(
            semboller
        )

        if not temiz_semboller:
            raise ValueError(
                "Taranacak en az bir hisse sembolü gereklidir."
            )

        basarili_sonuclar: list[StockAnalysisResult] = []
        hatalar: list[ScanFailure] = []

        toplam = len(temiz_semboller)

        for sira, sembol in enumerate(
            temiz_semboller,
            start=1,
        ):
            if ilerleme_bildirimi is not None:
                ilerleme_bildirimi(
                    sira,
                    toplam,
                    sembol,
                )

            try:
                sonuc = self._analiz_motoru.analiz_et(
                    sembol
                )

            except (
                ValueError,
                StockAnalyzerError,
            ) as hata:
                hatalar.append(
                    ScanFailure(
                        sembol=sembol,
                        hata=str(hata),
                    )
                )
                continue

            basarili_sonuclar.append(sonuc)

        sirali_sonuclar = sorted(
            basarili_sonuclar,
            key=lambda sonuc: (
                -sonuc.sinyal.skor,
                -sonuc.risk_plani.risk_odul_orani,
                sonuc.sembol,
            ),
        )

        return StockScanResult(
            basarili_sonuclar=tuple(
                sirali_sonuclar
            ),
            hatalar=tuple(hatalar),
        )


class BatchStockScanner:
    """
    Birden fazla hisseyi tek toplu veri indirmesi üzerinden analiz eder.

    StockScanner ile aynı sonuç modelini üretir; farkı, geniş BIST evrenlerinde
    her sembol için ayrı ağ çağrısı yapmak yerine veriyi parçalar halinde
    indirmesidir.
    """

    def __init__(
        self,
        analiz_motoru: StockAnalyzer | None = None,
        veri_getirici: Callable[..., BatchMarketDataResult] = (
            toplu_fiyat_verisi_getir
        ),
    ) -> None:
        self._analiz_motoru = analiz_motoru or StockAnalyzer()
        self._veri_getirici = veri_getirici

    def tara(
        self,
        semboller: Iterable[str],
        ilerleme_bildirimi: (
            Callable[[int, int, str], None] | None
        ) = None,
    ) -> StockScanResult:
        temiz_semboller = _sembolleri_hazirla(semboller)
        if not temiz_semboller:
            raise ValueError(
                "Taranacak en az bir hisse sembolü gereklidir."
            )

        veri_sonucu = self._veri_getirici(
            temiz_semboller,
            islem_gunu=160,
            indirme_donemi="1y",
        )
        veri_hatalari = {
            hata.sembol: hata.hata for hata in veri_sonucu.hatalar
        }

        basarili_sonuclar: list[StockAnalysisResult] = []
        hatalar: list[ScanFailure] = []
        toplam = len(temiz_semboller)

        for sira, sembol in enumerate(temiz_semboller, start=1):
            if ilerleme_bildirimi is not None:
                ilerleme_bildirimi(sira, toplam, sembol)

            fiyat_verisi = veri_sonucu.veriler.get(sembol)
            if fiyat_verisi is None:
                hatalar.append(
                    ScanFailure(
                        sembol=sembol,
                        hata=veri_hatalari.get(
                            sembol, "Toplu veride sembol bulunamadı."
                        ),
                    )
                )
                continue

            try:
                sonuc = self._analiz_motoru.veriden_analiz_et(
                    sembol=sembol,
                    fiyat_verisi=fiyat_verisi,
                )
            except (ValueError, StockAnalyzerError) as hata:
                hatalar.append(
                    ScanFailure(sembol=sembol, hata=str(hata))
                )
                continue

            basarili_sonuclar.append(sonuc)

        sirali_sonuclar = sorted(
            basarili_sonuclar,
            key=lambda sonuc: (
                -sonuc.sinyal.skor,
                -sonuc.risk_plani.risk_odul_orani,
                -sonuc.hacim_orani,
                sonuc.sembol,
            ),
        )

        return StockScanResult(
            basarili_sonuclar=tuple(sirali_sonuclar),
            hatalar=tuple(hatalar),
        )


def _sembolleri_hazirla(
    semboller: Iterable[str],
) -> list[str]:
    """
    Sembolleri temizler, BIST uzantısını ekler ve tekrarları siler.
    """
    sonuc: list[str] = []
    gorulenler: set[str] = set()

    for sembol in semboller:
        temiz_sembol = str(
            sembol
        ).lstrip("\ufeff").strip().upper()

        if not temiz_sembol:
            continue

        if "." not in temiz_sembol:
            temiz_sembol = (
                f"{temiz_sembol}.IS"
            )

        if temiz_sembol in gorulenler:
            continue

        gorulenler.add(temiz_sembol)
        sonuc.append(temiz_sembol)

    return sonuc