from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pandas as pd

from backend.app.analysis.stock_scanner import BatchStockScanner
from backend.app.data.batch_market_data import (
    BatchMarketDataFailure,
    BatchMarketDataResult,
)


def ornek_sonuc(sembol: str, skor: int, risk_odul: float, hacim: float) -> Any:
    return SimpleNamespace(
        sembol=sembol,
        hacim_orani=hacim,
        sinyal=SimpleNamespace(skor=skor, karar="Pozitif Teknik Görünüm"),
        risk_plani=SimpleNamespace(risk_odul_orani=risk_odul),
    )


class SahteAnalizMotoru:
    def __init__(self) -> None:
        self.cagrilar: list[str] = []

    def veriden_analiz_et(self, sembol: str, fiyat_verisi: pd.DataFrame) -> Any:
        self.cagrilar.append(sembol)
        assert not fiyat_verisi.empty
        if sembol == "AAA.IS":
            return ornek_sonuc(sembol, 70, 2.0, 1.2)
        return ornek_sonuc(sembol, 70, 2.0, 1.8)


def test_batch_tarama_veriyi_bir_kez_alir_ve_hacimle_siralar() -> None:
    cagrilar: list[tuple[str, ...]] = []
    veri = pd.DataFrame({"Close": [1.0]})

    def veri_getirici(semboller: object, **_kwargs: object) -> BatchMarketDataResult:
        temiz = tuple(semboller)  # type: ignore[arg-type]
        cagrilar.append(temiz)
        return BatchMarketDataResult(
            veriler={sembol: veri for sembol in temiz},
            hatalar=(),
        )

    analiz = SahteAnalizMotoru()
    sonuc = BatchStockScanner(
        analiz_motoru=analiz,  # type: ignore[arg-type]
        veri_getirici=veri_getirici,
    ).tara(["AAA", "BBB"])

    assert cagrilar == [("AAA.IS", "BBB.IS")]
    assert analiz.cagrilar == ["AAA.IS", "BBB.IS"]
    assert [x.sembol for x in sonuc.basarili_sonuclar] == [
        "BBB.IS",
        "AAA.IS",
    ]


def test_batch_tarama_veri_hatasini_korur() -> None:
    veri = pd.DataFrame({"Close": [1.0]})

    def veri_getirici(semboller: object, **_kwargs: object) -> BatchMarketDataResult:
        _ = tuple(semboller)  # type: ignore[arg-type]
        return BatchMarketDataResult(
            veriler={"AAA.IS": veri},
            hatalar=(
                BatchMarketDataFailure(
                    sembol="BBB.IS",
                    hata="Veri bulunamadı.",
                ),
            ),
        )

    sonuc = BatchStockScanner(
        analiz_motoru=SahteAnalizMotoru(),  # type: ignore[arg-type]
        veri_getirici=veri_getirici,
    ).tara(["AAA", "BBB"])

    assert sonuc.basarili_sayisi == 1
    assert sonuc.hatali_sayisi == 1
    assert sonuc.hatalar[0].sembol == "BBB.IS"
