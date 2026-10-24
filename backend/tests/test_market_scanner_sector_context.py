from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from backend.app.analysis.bist_universe import BistUniverse
from backend.app.analysis.market_scanner import (
    BistMarketScannerService,
    MarketScanRequest,
    aday_tablosu_kayitlari,
)
from backend.app.analysis.stock_scanner import StockScanResult
from backend.app.sector_analysis.sector_candidate_context import (
    CandidateSectorContext,
    CandidateSectorContextBundle,
)


def candidate():
    return SimpleNamespace(
        sembol="AAA.IS",
        analiz_tarihi="2026-08-04",
        kapanis=100.0,
        rsi14=55.0,
        atr_yuzde=2.0,
        hacim_orani=1.3,
        sinyal=SimpleNamespace(
            skor=70,
            karar="Nötr Teknik Görünüm",
            pozitif_nedenler=("Trend korunuyor.",),
            riskler=("Teyit gerekli.",),
        ),
        risk_plani=SimpleNamespace(
            giris_fiyati=100.0,
            stop_loss=95.0,
            hedef_fiyat=110.0,
            risk_odul_orani=1.0,
            filtreyi_gecti=False,
            risk_notu="Orta Volatiliteli",
        ),
    )


class Repo:
    def evreni_yukle(self, evren_adi, internetten_guncelle=True):
        return BistUniverse(
            ad=evren_adi,
            endeks_kodu="XU100",
            semboller=("AAA.IS",),
            tarih="04/08/2026",
            kaynak="test",
            resmi_kaynaktan_guncel=True,
        )


class Scanner:
    def tara(self, semboller, ilerleme_bildirimi=None):
        return StockScanResult(
            basarili_sonuclar=(candidate(),),
            hatalar=(),
        )


def context():
    return CandidateSectorContext(
        symbol="AAA.IS",
        sector_code="XULAS",
        sector_name="Ulaştırma",
        sector_score=68,
        sector_status="Pozitif",
        sector_confidence="Orta",
        relative_composite=4.22,
        label="Pozitif sektör desteği",
    )


def test_sektor_baglami_aday_sirasini_ve_teknik_skoru_degistirmez(tmp_path: Path):
    def provider(symbols, reference_universe):
        assert symbols == ("AAA.IS",)
        assert reference_universe == "BIST 100"
        return CandidateSectorContextBundle(
            contexts={"AAA.IS": context()},
            reference_universe=reference_universe,
        )

    result = BistMarketScannerService(
        evren_repository=Repo(),
        tarayici=Scanner(),
        izleme_listesi_yolu=tmp_path / "favoriler.txt",
        sector_context_provider=provider,
    ).calistir(
        MarketScanRequest(
            evren="BIST 100",
            profil_adi="dengeli",
            sektor_baglami_aktif=True,
        )
    )

    assert result.adaylar[0].sembol == "AAA.IS"
    assert result.adaylar[0].sinyal.skor == 70
    assert result.sektor_baglamlari["AAA.IS"].sector_score == 68


def test_sektor_baglami_hatasi_teknik_taramayi_durdurmaz(tmp_path: Path):
    def provider(_symbols, _reference_universe):
        raise RuntimeError("sektör veri hatası")

    result = BistMarketScannerService(
        evren_repository=Repo(),
        tarayici=Scanner(),
        izleme_listesi_yolu=tmp_path / "favoriler.txt",
        sector_context_provider=provider,
    ).calistir(
        MarketScanRequest(
            evren="BIST 100",
            profil_adi="dengeli",
            sektor_baglami_aktif=True,
        )
    )

    assert len(result.adaylar) == 1
    assert result.sektor_baglamlari == {}
    assert "Teknik tarama sonucu değiştirilmedi" in result.sektor_baglami_uyarisi


def test_aday_tablosu_sektor_baglamini_ayri_kolonlarda_gosterir(tmp_path: Path):
    def provider(_symbols, reference_universe):
        return CandidateSectorContextBundle(
            contexts={"AAA.IS": context()},
            reference_universe=reference_universe,
        )

    result = BistMarketScannerService(
        evren_repository=Repo(),
        tarayici=Scanner(),
        izleme_listesi_yolu=tmp_path / "favoriler.txt",
        sector_context_provider=provider,
    ).calistir(
        MarketScanRequest(
            evren="BIST 100",
            profil_adi="dengeli",
            sektor_baglami_aktif=True,
        )
    )

    row = aday_tablosu_kayitlari(result)[0]
    assert row["Sektör"] == "Ulaştırma"
    assert row["Sektör skoru"] == 68
    assert row["Sektör görünümü"] == "Pozitif"
    assert row["Sektör güveni"] == "Orta"
    assert row["Sektör bağlamı"] == "Pozitif sektör desteği"
    assert row["Sektör RS"] == 4.22
