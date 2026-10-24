from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.analysis.bist_universe import BistUniverse
from backend.app.analysis.market_scanner import (
    BistMarketScannerService,
    MarketScanRequest,
    aday_tablosu_kayitlari,
    ozel_sembol_metinini_ayristir,
)
from backend.app.analysis.stock_scanner import StockScanResult


def ornek_sonuc(
    sembol: str,
    skor: int,
    karar: str,
    hacim_orani: float,
    risk_odul: float = 2.0,
) -> Any:
    return SimpleNamespace(
        sembol=sembol,
        analiz_tarihi="2026-07-24",
        kapanis=100.0,
        rsi14=55.0,
        atr_yuzde=2.5,
        hacim_orani=hacim_orani,
        sinyal=SimpleNamespace(
            skor=skor,
            karar=karar,
            pozitif_nedenler=("Trend olumlu.",),
            riskler=("Dirence yakın.",),
        ),
        risk_plani=SimpleNamespace(
            giris_fiyati=100.0,
            stop_loss=95.0,
            hedef_fiyat=110.0,
            risk_odul_orani=risk_odul,
            filtreyi_gecti=risk_odul >= 2.0,
            risk_notu="Orta Volatiliteli",
        ),
    )


class SahteEvrenDeposu:
    def evreni_yukle(
        self,
        evren_adi: str,
        internetten_guncelle: bool = True,
    ) -> BistUniverse:
        assert internetten_guncelle is True
        return BistUniverse(
            ad=evren_adi,
            endeks_kodu="XU100",
            semboller=("AAA.IS", "BBB.IS", "CCC.IS"),
            tarih="27/07/2026",
            kaynak="Test evreni",
            resmi_kaynaktan_guncel=True,
        )


class SahteTarayici:
    def tara(self, semboller: object, ilerleme_bildirimi: object = None) -> StockScanResult:
        assert tuple(semboller) == ("AAA.IS", "BBB.IS", "CCC.IS")
        return StockScanResult(
            basarili_sonuclar=(
                ornek_sonuc("AAA.IS", 80, "Pozitif Teknik Görünüm", 1.5),
                ornek_sonuc("BBB.IS", 60, "Nötr Teknik Görünüm", 1.1),
                ornek_sonuc("CCC.IS", 40, "Negatif Teknik Görünüm", 0.7),
            ),
            hatalar=(),
        )


def test_dengeli_profil_adaylari_filtreler_ve_sinirlar(tmp_path: Path) -> None:
    servis = BistMarketScannerService(
        evren_repository=SahteEvrenDeposu(),  # type: ignore[arg-type]
        tarayici=SahteTarayici(),  # type: ignore[arg-type]
        izleme_listesi_yolu=tmp_path / "favoriler.txt",
    )

    sonuc = servis.calistir(
        MarketScanRequest(
            evren="BIST 100",
            profil_adi="dengeli",
            maksimum_aday=1,
        )
    )

    assert sonuc.evren_sembol_sayisi == 3
    assert sonuc.filtrelenmis.aday_sayisi == 2
    assert sonuc.gosterilen_aday_sayisi == 1
    assert sonuc.adaylar[0].sembol == "AAA.IS"

    kayit = aday_tablosu_kayitlari(sonuc)[0]
    assert kayit["Hisse"] == "AAA"
    assert kayit["Durum"] == "Teknik aday"
    assert kayit["Risk/Getiri"] == 2.0


def test_ozel_sembol_metni_ayristirilir() -> None:
    assert ozel_sembol_metinini_ayristir(
        " thyao, ASELS.IS; TUPRS\nTHYAO "
    ) == ("THYAO.IS", "ASELS.IS", "TUPRS.IS")


def test_gecersiz_maksimum_aday_reddedilir() -> None:
    with pytest.raises(ValueError, match="Maksimum aday"):
        MarketScanRequest(maksimum_aday=0)


def test_ozel_sembol_metnindeki_bom_temizlenir() -> None:
    assert ozel_sembol_metinini_ayristir("\ufeffBIGEN, CMBTN") == (
        "BIGEN.IS",
        "CMBTN.IS",
    )
def test_vbts_filtresi_tarayıcıdan_once_uygulanir(tmp_path: Path) -> None:
    from datetime import date, datetime, timedelta, timezone

    from backend.app.compliance.vbts_dataset import VbtsDataset
    from backend.app.compliance.vbts_models import VbtsMeasure
    from backend.app.compliance.vbts_scan_filter import VbtsScanFilter
    from backend.app.compliance.vbts_source_status import VbtsSourceStatus

    class VbtsFiltreliSahteTarayici:
        def tara(
            self,
            semboller: object,
            ilerleme_bildirimi: object = None,
        ) -> StockScanResult:
            assert tuple(semboller) == ("AAA.IS", "CCC.IS")

            return StockScanResult(
                basarili_sonuclar=(
                    ornek_sonuc(
                        "AAA.IS",
                        80,
                        "Pozitif Teknik Görünüm",
                        1.5,
                    ),
                    ornek_sonuc(
                        "CCC.IS",
                        40,
                        "Negatif Teknik Görünüm",
                        0.7,
                    ),
                ),
                hatalar=(),
            )

    fetched_at = datetime(2026, 7, 28, 18, 0, tzinfo=timezone.utc)

    dataset = VbtsDataset(
        measures=[
            VbtsMeasure(
                symbol="BBB",
                measure_type="BRUT_TAKAS",
                start_date=date(2026, 7, 20),
                end_date=date(2026, 8, 19),
                source="KAP",
                source_reference="bildirim-bbb",
            )
        ],
        status=VbtsSourceStatus(
            source="KAP",
            fetched_at=fetched_at,
            is_verified=True,
            record_count=1,
        ),
    )

    servis = BistMarketScannerService(
        evren_repository=SahteEvrenDeposu(),  # type: ignore[arg-type]
        tarayici=VbtsFiltreliSahteTarayici(),  # type: ignore[arg-type]
        izleme_listesi_yolu=tmp_path / "favoriler.txt",
        vbts_scan_filter=VbtsScanFilter(
            dataset=dataset,
            maximum_age=timedelta(hours=6),
        ),
        vbts_control_date=date(2026, 7, 28),
        vbts_control_time=fetched_at + timedelta(hours=1),
    )

    sonuc = servis.calistir(
        MarketScanRequest(
            evren="BIST 100",
            profil_adi="dengeli",
        )
    )

    assert sonuc.evren_sembol_sayisi == 2
def test_vbts_engelleri_tarama_sonucunda_raporlanir(tmp_path: Path) -> None:
    from datetime import date, datetime, timedelta, timezone

    from backend.app.compliance.vbts_dataset import VbtsDataset
    from backend.app.compliance.vbts_models import VbtsMeasure
    from backend.app.compliance.vbts_scan_filter import VbtsScanFilter
    from backend.app.compliance.vbts_source_status import VbtsSourceStatus

    class RaporlamaSahteTarayici:
        def tara(
            self,
            semboller: object,
            ilerleme_bildirimi: object = None,
        ) -> StockScanResult:
            assert tuple(semboller) == ("AAA.IS", "CCC.IS")

            return StockScanResult(
                basarili_sonuclar=(
                    ornek_sonuc(
                        "AAA.IS",
                        80,
                        "Pozitif Teknik Görünüm",
                        1.5,
                    ),
                    ornek_sonuc(
                        "CCC.IS",
                        40,
                        "Negatif Teknik Görünüm",
                        0.7,
                    ),
                ),
                hatalar=(),
            )

    fetched_at = datetime(
        2026,
        7,
        28,
        18,
        0,
        tzinfo=timezone.utc,
    )

    dataset = VbtsDataset(
        measures=[
            VbtsMeasure(
                symbol="BBB",
                measure_type="BRUT_TAKAS",
                start_date=date(2026, 7, 20),
                end_date=date(2026, 8, 19),
                source="KAP",
                source_reference="bildirim-bbb",
            )
        ],
        status=VbtsSourceStatus(
            source="KAP",
            fetched_at=fetched_at,
            is_verified=True,
            record_count=1,
        ),
    )

    servis = BistMarketScannerService(
        evren_repository=SahteEvrenDeposu(),  # type: ignore[arg-type]
        tarayici=RaporlamaSahteTarayici(),  # type: ignore[arg-type]
        izleme_listesi_yolu=tmp_path / "favoriler.txt",
        vbts_scan_filter=VbtsScanFilter(
            dataset=dataset,
            maximum_age=timedelta(hours=6),
        ),
        vbts_control_date=date(2026, 7, 28),
        vbts_control_time=fetched_at + timedelta(hours=1),
    )

    sonuc = servis.calistir(
        MarketScanRequest(
            evren="BIST 100",
            profil_adi="dengeli",
        )
    )

    assert sonuc.vbts_engellenen_semboller == ("BBB.IS",)
    assert sonuc.vbts_engelleme_nedenleri == {
        "BBB.IS": ("BRUT_TAKAS",)
    }