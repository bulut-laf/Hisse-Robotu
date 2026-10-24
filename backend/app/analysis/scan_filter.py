from __future__ import annotations

from dataclasses import dataclass

from .stock_analyzer import StockAnalysisResult
from .stock_scanner import (
    ScanFailure,
    StockScanResult,
)


POZITIF_GORUNUM = "Pozitif Teknik Görünüm"
NOTR_GORUNUM = "Nötr Teknik Görünüm"
NEGATIF_GORUNUM = "Negatif Teknik Görünüm"

TUM_GORUNUMLER = (
    POZITIF_GORUNUM,
    NOTR_GORUNUM,
    NEGATIF_GORUNUM,
)


@dataclass(frozen=True)
class ScanFilterCriteria:
    """Çoklu hisse taramasında uygulanacak filtre koşulları."""

    minimum_skor: int = 0
    minimum_hacim_orani: float = 0.0
    risk_odul_filtresi_gerekli: bool = False
    izin_verilen_gorunumler: tuple[str, ...] = TUM_GORUNUMLER

    def __post_init__(self) -> None:
        if not 0 <= self.minimum_skor <= 100:
            raise ValueError(
                "Minimum skor 0 ile 100 arasında olmalıdır."
            )

        if self.minimum_hacim_orani < 0:
            raise ValueError(
                "Minimum hacim oranı negatif olamaz."
            )

        if not self.izin_verilen_gorunumler:
            raise ValueError(
                "En az bir teknik görünüm seçilmelidir."
            )

        gecersiz_gorunumler = set(
            self.izin_verilen_gorunumler
        ).difference(TUM_GORUNUMLER)

        if gecersiz_gorunumler:
            raise ValueError(
                "Geçersiz teknik görünüm: "
                + ", ".join(
                    sorted(gecersiz_gorunumler)
                )
            )


@dataclass(frozen=True)
class ScanRejection:
    """Filtre tarafından elenen hisse ve eleme nedenleri."""

    sembol: str
    nedenler: tuple[str, ...]
    sonuc: StockAnalysisResult | None = None


@dataclass(frozen=True)
class FilteredScanResult:
    """Filtre uygulanmış tarama sonucunu temsil eder."""

    adaylar: tuple[StockAnalysisResult, ...]
    elenenler: tuple[ScanRejection, ...]
    hatalar: tuple[ScanFailure, ...]

    @property
    def aday_sayisi(self) -> int:
        return len(self.adaylar)

    @property
    def elenen_sayisi(self) -> int:
        return len(self.elenenler)

    @property
    def hatali_sayisi(self) -> int:
        return len(self.hatalar)

    @property
    def toplam_sayisi(self) -> int:
        return (
            self.aday_sayisi
            + self.elenen_sayisi
            + self.hatali_sayisi
        )


def tarama_sonucunu_filtrele(
    tarama: StockScanResult,
    kriterler: ScanFilterCriteria,
) -> FilteredScanResult:
    """
    Başarılı tarama sonuçlarına belirtilen filtreleri uygular.

    Elenen hisselerin bütün analiz sonucu korunur.
    """
    adaylar: list[StockAnalysisResult] = []
    elenenler: list[ScanRejection] = []

    for sonuc in tarama.basarili_sonuclar:
        nedenler = _eleme_nedenlerini_bul(
            sonuc=sonuc,
            kriterler=kriterler,
        )

        if nedenler:
            elenenler.append(
                ScanRejection(
                    sembol=sonuc.sembol,
                    nedenler=tuple(nedenler),
                    sonuc=sonuc,
                )
            )
        else:
            adaylar.append(sonuc)

    return FilteredScanResult(
        adaylar=tuple(adaylar),
        elenenler=tuple(elenenler),
        hatalar=tarama.hatalar,
    )


def _eleme_nedenlerini_bul(
    sonuc: StockAnalysisResult,
    kriterler: ScanFilterCriteria,
) -> list[str]:
    nedenler: list[str] = []

    if sonuc.sinyal.skor < kriterler.minimum_skor:
        nedenler.append(
            f"Sinyal skoru {sonuc.sinyal.skor}; "
            f"minimum {kriterler.minimum_skor} gerekli."
        )

    if (
        sonuc.hacim_orani
        < kriterler.minimum_hacim_orani
    ):
        nedenler.append(
            f"Hacim oranı {sonuc.hacim_orani:.2f}x; "
            f"minimum {kriterler.minimum_hacim_orani:.2f}x "
            "gerekli."
        )

    if (
        kriterler.risk_odul_filtresi_gerekli
        and not sonuc.risk_plani.filtreyi_gecti
    ):
        nedenler.append(
            "Risk/ödül filtresini geçemedi."
        )

    if (
        sonuc.sinyal.karar
        not in kriterler.izin_verilen_gorunumler
    ):
        nedenler.append(
            "Teknik görünüm izin verilen grupta değil: "
            f"{sonuc.sinyal.karar}."
        )

    return nedenler