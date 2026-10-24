from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.analysis.bist_universe import BistUniverse
from backend.app.analysis.stock_scanner import StockScanResult
from backend.app.compliance.vbts_dataset import VbtsDataset
from backend.app.compliance.vbts_models import VbtsMeasure
from backend.app.compliance.vbts_source_status import VbtsSourceStatus


class SahteEvrenDeposu:
    def evreni_yukle(
        self,
        evren_adi: str,
        internetten_guncelle: bool = True,
    ) -> BistUniverse:
        return BistUniverse(
            ad=evren_adi,
            endeks_kodu="XU100",
            semboller=("AAA.IS", "BBB.IS"),
            tarih="29/07/2026",
            kaynak="Test evreni",
            resmi_kaynaktan_guncel=True,
        )


class SahteTarayici:
    def tara(
        self,
        semboller: object,
        ilerleme_bildirimi: object = None,
    ) -> StockScanResult:
        assert tuple(semboller) == ("AAA.IS",)

        sonuc = SimpleNamespace(
            sembol="AAA.IS",
            analiz_tarihi="2026-07-29",
            kapanis=100.0,
            rsi14=55.0,
            atr_yuzde=2.0,
            hacim_orani=1.3,
            sinyal=SimpleNamespace(
                skor=80,
                karar="Pozitif Teknik Görünüm",
                pozitif_nedenler=("Trend olumlu.",),
                riskler=(),
            ),
            risk_plani=SimpleNamespace(
                giris_fiyati=100.0,
                stop_loss=95.0,
                hedef_fiyat=110.0,
                risk_odul_orani=2.0,
                filtreyi_gecti=True,
                risk_notu="Orta Volatiliteli",
            ),
        )

        return StockScanResult(
            basarili_sonuclar=(sonuc,),
            hatalar=(),
        )


class SahteKapVbtsService:
    def fetch_dataset(
        self,
        *,
        start_date: date,
        end_date: date,
        fetched_at: datetime,
    ) -> VbtsDataset:
        assert start_date == date(2026, 7, 22)
        assert end_date == date(2026, 7, 29)
        assert fetched_at == datetime(
            2026,
            7,
            29,
            12,
            0,
            tzinfo=timezone.utc,
        )

        return VbtsDataset(
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


def test_dashboard_market_scanner_factory_vbts_korumali_servis_olusturur(
    tmp_path: Path,
) -> None:
    from backend.app.compliance.dashboard_market_scanner_factory import (
        build_protected_market_scanner,
    )

    service = build_protected_market_scanner(
        kap_vbts_service=SahteKapVbtsService(),
        now_provider=lambda: datetime(
            2026,
            7,
            29,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        lookback_days=7,
        maximum_age=timedelta(hours=6),
        evren_repository=SahteEvrenDeposu(),
        tarayici=SahteTarayici(),
        izleme_listesi_yolu=tmp_path / "favoriler.txt",
    )

    from backend.app.analysis.market_scanner import MarketScanRequest

    sonuc = service.calistir(
        MarketScanRequest(
            evren="BIST 100",
            profil_adi="dengeli",
        )
    )

    assert sonuc.evren_sembol_sayisi == 1
    assert sonuc.vbts_engellenen_semboller == ("BBB.IS",)


def test_dashboard_market_scanner_factory_kap_hatasinda_servis_olusturmaz() -> None:
    from backend.app.compliance.dashboard_market_scanner_factory import (
        DashboardMarketScannerFactoryError,
        build_protected_market_scanner,
    )

    class HataVerenKapServisi:
        def fetch_dataset(
            self,
            *,
            start_date: date,
            end_date: date,
            fetched_at: datetime,
        ) -> VbtsDataset:
            raise RuntimeError("KAP erişilemedi.")

    with pytest.raises(
        DashboardMarketScannerFactoryError,
        match="KAP/VBTS korumalı tarama hazırlanamadı",
    ):
        build_protected_market_scanner(
            kap_vbts_service=HataVerenKapServisi(),
            now_provider=lambda: datetime(
                2026,
                7,
                29,
                12,
                0,
                tzinfo=timezone.utc,
            ),
        )
