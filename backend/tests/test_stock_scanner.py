from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.analysis.stock_analyzer import (
    StockAnalyzerError,
)
from backend.app.analysis.stock_scanner import (
    StockScanner,
)


def ornek_sonuc(
    sembol: str,
    skor: int,
    karar: str,
    risk_odul_orani: float,
) -> Any:
    """
    Tarayıcı testlerinde kullanılacak sade analiz sonucu.
    """
    return SimpleNamespace(
        sembol=sembol,
        sinyal=SimpleNamespace(
            skor=skor,
            karar=karar,
        ),
        risk_plani=SimpleNamespace(
            risk_odul_orani=risk_odul_orani,
        ),
    )


class SahteAnalizMotoru:
    """
    İnternet bağlantısı olmadan önceden hazırlanmış
    sonuçları döndüren test analiz motoru.
    """

    def __init__(
        self,
        sonuclar: dict[str, Any],
    ) -> None:
        self.sonuclar = sonuclar
        self.cagrilar: list[str] = []

    def analiz_et(
        self,
        sembol: str,
    ) -> Any:
        self.cagrilar.append(sembol)

        sonuc = self.sonuclar[sembol]

        if isinstance(sonuc, Exception):
            raise sonuc

        return sonuc


def test_semboller_temizlenir_ve_skorla_siralanir() -> None:
    analiz_motoru = SahteAnalizMotoru(
        {
            "THYAO.IS": ornek_sonuc(
                sembol="THYAO.IS",
                skor=40,
                karar="Nötr Teknik Görünüm",
                risk_odul_orani=1.20,
            ),
            "ASELS.IS": ornek_sonuc(
                sembol="ASELS.IS",
                skor=65,
                karar="Pozitif Teknik Görünüm",
                risk_odul_orani=2.10,
            ),
        }
    )

    tarama = StockScanner(
        analiz_motoru=analiz_motoru,
    ).tara(
        [
            " thyao ",
            "ASELS.IS",
            "THYAO",
            "",
        ]
    )

    assert analiz_motoru.cagrilar == [
        "THYAO.IS",
        "ASELS.IS",
    ]

    assert [
        sonuc.sembol
        for sonuc in tarama.basarili_sonuclar
    ] == [
        "ASELS.IS",
        "THYAO.IS",
    ]

    assert tarama.toplam_sembol == 2
    assert tarama.basarili_sayisi == 2
    assert tarama.hatali_sayisi == 0


def test_esit_skorlarda_risk_odul_oranina_gore_siralanir() -> None:
    analiz_motoru = SahteAnalizMotoru(
        {
            "AAA.IS": ornek_sonuc(
                sembol="AAA.IS",
                skor=60,
                karar="Nötr Teknik Görünüm",
                risk_odul_orani=1.50,
            ),
            "BBB.IS": ornek_sonuc(
                sembol="BBB.IS",
                skor=60,
                karar="Nötr Teknik Görünüm",
                risk_odul_orani=2.20,
            ),
        }
    )

    tarama = StockScanner(
        analiz_motoru=analiz_motoru,
    ).tara(
        [
            "AAA",
            "BBB",
        ]
    )

    assert [
        sonuc.sembol
        for sonuc in tarama.basarili_sonuclar
    ] == [
        "BBB.IS",
        "AAA.IS",
    ]


def test_gorunum_sayilari_dogru_hesaplanir() -> None:
    analiz_motoru = SahteAnalizMotoru(
        {
            "AAA.IS": ornek_sonuc(
                sembol="AAA.IS",
                skor=80,
                karar="Pozitif Teknik Görünüm",
                risk_odul_orani=2.50,
            ),
            "BBB.IS": ornek_sonuc(
                sembol="BBB.IS",
                skor=55,
                karar="Nötr Teknik Görünüm",
                risk_odul_orani=1.80,
            ),
            "CCC.IS": ornek_sonuc(
                sembol="CCC.IS",
                skor=25,
                karar="Negatif Teknik Görünüm",
                risk_odul_orani=0.80,
            ),
        }
    )

    tarama = StockScanner(
        analiz_motoru=analiz_motoru,
    ).tara(
        [
            "AAA",
            "BBB",
            "CCC",
        ]
    )

    assert tarama.pozitif_sayisi == 1
    assert tarama.notr_sayisi == 1
    assert tarama.negatif_sayisi == 1


def test_bir_hata_taramayi_durdurmaz() -> None:
    analiz_motoru = SahteAnalizMotoru(
        {
            "AAA.IS": ornek_sonuc(
                sembol="AAA.IS",
                skor=70,
                karar="Pozitif Teknik Görünüm",
                risk_odul_orani=2.20,
            ),
            "HATALI.IS": StockAnalyzerError(
                "Veri bulunamadı."
            ),
            "BBB.IS": ornek_sonuc(
                sembol="BBB.IS",
                skor=45,
                karar="Nötr Teknik Görünüm",
                risk_odul_orani=1.10,
            ),
        }
    )

    tarama = StockScanner(
        analiz_motoru=analiz_motoru,
    ).tara(
        [
            "AAA",
            "HATALI",
            "BBB",
        ]
    )

    assert tarama.toplam_sembol == 3
    assert tarama.basarili_sayisi == 2
    assert tarama.hatali_sayisi == 1

    assert tarama.hatalar[0].sembol == "HATALI.IS"
    assert "Veri bulunamadı" in tarama.hatalar[0].hata


def test_ilerleme_bildirimi_dogru_cagrilir() -> None:
    analiz_motoru = SahteAnalizMotoru(
        {
            "AAA.IS": ornek_sonuc(
                sembol="AAA.IS",
                skor=50,
                karar="Nötr Teknik Görünüm",
                risk_odul_orani=1.50,
            ),
            "BBB.IS": ornek_sonuc(
                sembol="BBB.IS",
                skor=60,
                karar="Nötr Teknik Görünüm",
                risk_odul_orani=1.80,
            ),
        }
    )

    bildirimler: list[
        tuple[int, int, str]
    ] = []

    StockScanner(
        analiz_motoru=analiz_motoru,
    ).tara(
        semboller=[
            "AAA",
            "BBB",
        ],
        ilerleme_bildirimi=lambda sira, toplam, sembol: (
            bildirimler.append(
                (
                    sira,
                    toplam,
                    sembol,
                )
            )
        ),
    )

    assert bildirimler == [
        (
            1,
            2,
            "AAA.IS",
        ),
        (
            2,
            2,
            "BBB.IS",
        ),
    ]


def test_bos_sembol_listesi_kabul_edilmez() -> None:
    analiz_motoru = SahteAnalizMotoru({})

    with pytest.raises(
        ValueError,
        match="en az bir",
    ):
        StockScanner(
            analiz_motoru=analiz_motoru,
        ).tara(
            [
                "",
                "   ",
            ]
        )