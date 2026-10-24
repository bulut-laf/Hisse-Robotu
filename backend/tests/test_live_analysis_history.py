from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.data.data_freshness import DataFreshnessResult
from backend.app.history.backtest_history import (
    GUNCEL_TEKNIK_ANALIZ,
    METADATA_DOSYASI,
    BacktestHistoryRecord,
    BacktestHistoryStore,
)
from backend.app.history.backtest_history_backup import (
    BacktestHistoryBackupService,
)
from backend.app.history.backtest_history_comparison import (
    BacktestHistoryComparisonError,
    gecmis_kayitlarini_karsilastir,
)
from backend.app.history.backtest_history_summary import (
    gecmis_ozeti_hesapla,
    gecmis_performans_noktalari,
)
from backend.app.ui.live_analysis_dashboard import (
    LiveAnalysisDashboardService,
    LiveAnalysisRequest,
    LiveAnalysisResult,
)


DASHBOARD_DOSYASI = Path(__file__).resolve().parents[1] / "dashboard.py"


def sabit_saat(*zamanlar: datetime):
    degerler = iter(zamanlar)
    return lambda: next(degerler)


def guncel_sonuc() -> LiveAnalysisResult:
    haftalik = SimpleNamespace(yon="Nötr", skor=55)
    gunluk = SimpleNamespace(yon="Nötr", skor=52)
    saatlik = SimpleNamespace(yon="Pozitif", skor=61)
    teknik = SimpleNamespace(
        sembol="KUVVA.IS",
        veri_kimligi="veri-kuvva",
        analiz_kimligi="teknik-kuvva",
        teyit_skoru=54,
        teyit_durumu="Teknik Teyit Bekleniyor",
        haftalik=haftalik,
        gunluk=gunluk,
        saatlik=saatlik,
        pozitif_nedenler=("EMA9, EMA21 üzerinde.",),
        riskler=("RSI aşırı alıma yaklaşıyor.",),
    )
    pozisyon = SimpleNamespace(
        risk_butcesi=1_000.0,
        lot_sayisi=67,
        pozisyon_tutari=11_212.98,
        planlanan_risk=993.99,
    )
    plan = SimpleNamespace(
        plan_kimligi="plan-kuvva",
        karar="İşlem Yok",
        plan_tipi="Koşullu Alım Planı",
        son_kapanis=161.0,
        atr14=8.89,
        atr_yuzde=5.52,
        izleme_tetik_fiyati=166.02,
        giris_alt=166.02,
        giris_ust=167.36,
        referans_giris=167.36,
        stop_loss=152.52,
        hedef_1=189.61,
        hedef_2=197.03,
        risk_odul_1=1.5,
        risk_odul_2=2.0,
        pozisyon=pozisyon,
        beklenen_teyitler=("Teknik teyit skoru en az 60/100 olmalı.",),
        gecersizlik_kosullari=("154.30 altında kapanış.",),
        notlar=("Hedef 1 kısmi kâr hedefidir.",),
    )
    tazelik = DataFreshnessResult(
        durum="Kapanış verisi bekleniyor",
        son_veri_tarihi=date(2026, 7, 28),
        beklenen_tarih=date(2026, 7, 28),
        is_gunu_gecikmesi=0,
        kilitli=False,
        aciklama="Son tamamlanmış günlük bar 2026-07-28.",
    )
    return LiveAnalysisResult(
        paket=SimpleNamespace(sembol="KUVVA.IS"),
        teknik_teyit=teknik,
        islem_plani=plan,
        veri_tazeligi=tazelik,
        istek=LiveAnalysisRequest(
            "KUVVA",
            sermaye=100_000.0,
            azami_risk_orani=0.01,
        ),
    )


def test_guncel_analiz_servisi_istegi_sonucta_saklar() -> None:
    paket = object()
    teknik = object()
    plan = object()
    istek = LiveAnalysisRequest("KUVVA", sermaye=125_000, azami_risk_orani=0.02)

    sonuc = LiveAnalysisDashboardService(
        veri_getirici=lambda _sembol: paket,
        teknik_motoru=lambda _paket: teknik,
        plan_motoru=lambda **_kwargs: plan,
    ).calistir(istek)

    assert sonuc.istek is istek


def test_guncel_analiz_metadata_ve_csv_ile_kaydedilir(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(
        tmp_path,
        saat=sabit_saat(datetime(2026, 7, 29, 15, 22, tzinfo=timezone.utc)),
    )

    kayit = depo.guncel_analiz_kaydet(guncel_sonuc())
    metadata_yolu = tmp_path / kayit.kayit_kimligi / METADATA_DOSYASI

    assert kayit.analiz_turu == GUNCEL_TEKNIK_ANALIZ
    assert kayit.semboller == ("KUVVA.IS",)
    assert kayit.ozel_bilgiler["teknik_teyit"]["skor"] == 54
    assert kayit.ozel_bilgiler["islem_plani"]["karar"] == "İşlem Yok"
    assert kayit.ozel_bilgiler["risk_ve_pozisyon"]["lot_sayisi"] == 67
    assert metadata_yolu.is_file()
    assert {dosya.tur for dosya in kayit.dosyalar} == {"guncel_analiz_csv"}
    csv_baytlari = depo.dosya_baytlari(kayit, "guncel_analiz_csv")
    assert csv_baytlari.startswith(b"\xef\xbb\xbf")
    assert "islem_plani.karar,İşlem Yok" in csv_baytlari.decode("utf-8-sig")


def test_guncel_analiz_tekrarinda_ayni_kayit_guncellenir(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(
        tmp_path,
        saat=sabit_saat(
            datetime(2026, 7, 29, 15, 22, tzinfo=timezone.utc),
            datetime(2026, 7, 29, 15, 25, tzinfo=timezone.utc),
        ),
    )

    ilk = depo.guncel_analiz_kaydet(guncel_sonuc())
    ikinci = depo.guncel_analiz_kaydet(guncel_sonuc())

    assert ilk.kayit_kimligi == ikinci.kayit_kimligi
    assert ikinci.kaydedilme_zamani > ilk.kaydedilme_zamani
    assert len(tuple(tmp_path.iterdir())) == 1



def test_guncel_analiz_zip_yedegine_girer_ve_geri_yuklenir(
    tmp_path: Path,
) -> None:
    kaynak = BacktestHistoryStore(tmp_path / "kaynak")
    kayit = kaynak.guncel_analiz_kaydet(guncel_sonuc())
    yedek = BacktestHistoryBackupService(kaynak).yedek_olustur()

    hedef = BacktestHistoryStore(tmp_path / "hedef")
    sonuc = BacktestHistoryBackupService(hedef).yedegi_geri_yukle(yedek)
    geri_yuklenen = hedef.kayit_getir(kayit.kayit_kimligi)

    assert sonuc.geri_yuklenen == 1
    assert geri_yuklenen.analiz_turu == GUNCEL_TEKNIK_ANALIZ
    assert geri_yuklenen.ozel_bilgiler["islem_plani"]["hedef_2"] == 197.03
    assert hedef.dosya_baytlari(geri_yuklenen, "guncel_analiz_csv")

def test_eski_metadata_ozel_bilgiler_olmadan_okunur() -> None:
    ham = {
        "surum": 1,
        "kayit_kimligi": "tek_hisse_eski",
        "analiz_turu": "tek_hisse",
        "kaydedilme_zamani": "2026-07-25T20:00:00+03:00",
        "baslik": "Eski kayıt",
        "semboller": ["THYAO.IS"],
        "donem": "2025 — 2026",
        "tamamlanan_islem_sayisi": 1,
        "atlanan_islem_sayisi": 0,
        "bitis_sermayesi": 101000,
        "toplam_getiri_yuzde": 1,
        "maksimum_dusus_yuzde": 2,
        "guncel_dusus_yuzde": 0,
        "kar_faktoru": 1.1,
        "kazanma_yuzde": 50,
        "ortalama_sermaye_kullanim_yuzde": None,
        "maksimum_pozisyon": None,
        "analiz_kimligi": "a",
        "veri_kimligi": "v",
        "ayar_kimligi": "s",
        "dosyalar": [],
    }

    kayit = BacktestHistoryRecord.sozlukten(json.loads(json.dumps(ham)))

    assert kayit.ozel_bilgiler == {}


def test_guncel_kayit_performans_ozetini_bozmaz(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(tmp_path)
    guncel = depo.guncel_analiz_kaydet(guncel_sonuc())

    ozet = gecmis_ozeti_hesapla((guncel,))
    noktalar = gecmis_performans_noktalari((guncel,))

    assert ozet.toplam_kayit == 0
    assert ozet.medyan_getiri_yuzde is None
    assert noktalar == ()


def test_guncel_kayit_backtest_karsilastirmasina_girmez(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(
        tmp_path,
        saat=sabit_saat(
            datetime(2026, 7, 29, 15, 22, tzinfo=timezone.utc),
            datetime(2026, 7, 29, 15, 23, tzinfo=timezone.utc),
        ),
    )
    ilk = depo.guncel_analiz_kaydet(guncel_sonuc())
    ikinci_sonuc = guncel_sonuc()
    ikinci_sonuc.islem_plani.plan_kimligi = "plan-kuvva-2"
    ikinci = depo.guncel_analiz_kaydet(ikinci_sonuc)

    with pytest.raises(BacktestHistoryComparisonError, match="uygun değildir"):
        gecmis_kayitlarini_karsilastir(ilk, ikinci)


def test_dashboard_guncel_analizi_gecmise_baglar() -> None:
    kaynak = DASHBOARD_DOSYASI.read_text(encoding="utf-8")

    assert "depo.guncel_analiz_kaydet(sonuc)" in kaynak
    assert "Güncel teknik analiz, Analiz Geçmişi'ne kaydedildi." in kaynak
    assert '"Güncel Teknik Analiz": GUNCEL_TEKNIK_ANALIZ' in kaynak
    assert "guncel_analiz_gecmis_kaydi_goster" in kaynak
