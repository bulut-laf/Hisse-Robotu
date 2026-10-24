from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.app.history.backtest_history import (
    GECMIS_KLASORU_DEGISKENI,
    METADATA_DOSYASI,
    PORTFOY_ANALIZI,
    TEK_HISSE_ANALIZI,
    BacktestHistoryError,
    BacktestHistoryRecord,
    BacktestHistoryStore,
    HistoryArtifact,
    varsayilan_gecmis_klasoru,
)
from backend.tests.test_report_export import (
    portfoy_sonucu,
    tek_hisse_sonucu,
)


def sabit_saat(*zamanlar: datetime):
    degerler = iter(zamanlar)
    return lambda: next(degerler)


def test_varsayilan_gecmis_klasoru_ortam_degiskenini_kullanir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    hedef = tmp_path / "özel geçmiş"
    monkeypatch.setenv(GECMIS_KLASORU_DEGISKENI, str(hedef))

    assert varsayilan_gecmis_klasoru() == hedef


def test_tek_hisse_kaydi_metadata_csv_ve_pdf_olusturur(
    tmp_path: Path,
) -> None:
    depo = BacktestHistoryStore(
        tmp_path,
        saat=sabit_saat(datetime(2026, 7, 25, 18, 30, tzinfo=timezone.utc)),
    )

    kayit = depo.tek_hisse_kaydet(tek_hisse_sonucu())
    klasor = tmp_path / kayit.kayit_kimligi

    assert kayit.analiz_turu == TEK_HISSE_ANALIZI
    assert kayit.semboller == ("THYAO.IS",)
    assert kayit.tamamlanan_islem_sayisi == 1
    assert (klasor / METADATA_DOSYASI).is_file()
    assert {dosya.tur for dosya in kayit.dosyalar} == {
        "islemler_csv",
        "pdf",
    }
    assert depo.dosya_baytlari(kayit, "islemler_csv").startswith(
        b"\xef\xbb\xbf"
    )
    assert depo.dosya_baytlari(kayit, "pdf").startswith(b"%PDF-")


def test_portfoy_kaydi_uc_rapor_dosyasi_olusturur(
    tmp_path: Path,
) -> None:
    depo = BacktestHistoryStore(tmp_path)

    kayit = depo.portfoy_kaydet(portfoy_sonucu(atlanma_var=False))

    assert kayit.analiz_turu == PORTFOY_ANALIZI
    assert kayit.semboller == ("THYAO.IS", "TUPRS.IS", "ASELS.IS")
    assert kayit.ortalama_sermaye_kullanim_yuzde == pytest.approx(51.59)
    assert {dosya.tur for dosya in kayit.dosyalar} == {
        "katki_csv",
        "ozsermaye_csv",
        "pdf",
    }
    assert depo.dosya_baytlari(kayit, "katki_csv").startswith(
        b"\xef\xbb\xbf"
    )
    assert depo.dosya_baytlari(kayit, "ozsermaye_csv").startswith(
        b"\xef\xbb\xbf"
    )


def test_ayni_analiz_tekrar_kaydedilince_yeni_klasor_uretmez(
    tmp_path: Path,
) -> None:
    depo = BacktestHistoryStore(
        tmp_path,
        saat=sabit_saat(
            datetime(2026, 7, 25, 18, 30, tzinfo=timezone.utc),
            datetime(2026, 7, 25, 18, 35, tzinfo=timezone.utc),
        ),
    )

    ilk = depo.tek_hisse_kaydet(tek_hisse_sonucu())
    ikinci = depo.tek_hisse_kaydet(tek_hisse_sonucu())

    assert ilk.kayit_kimligi == ikinci.kayit_kimligi
    assert ikinci.kaydedilme_zamani > ilk.kaydedilme_zamani
    assert len(tuple(tmp_path.iterdir())) == 1
    assert depo.kayitlari_listele() == (ikinci,)


def test_kayitlar_yeni_tarihten_eskiye_siralanir(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(
        tmp_path,
        saat=sabit_saat(
            datetime(2026, 7, 25, 18, 30, tzinfo=timezone.utc),
            datetime(2026, 7, 25, 18, 31, tzinfo=timezone.utc),
        ),
    )
    tek = tek_hisse_sonucu()
    ikinci_ozet = replace(
        tek.ozet,
        analiz_kimligi="ikinci-analiz",
        veri_kimligi="ikinci-veri",
    )

    eski = depo.tek_hisse_kaydet(tek)
    yeni = depo.tek_hisse_kaydet(replace(tek, ozet=ikinci_ozet))

    assert depo.kayitlari_listele() == (yeni, eski)


def test_kayit_turu_filtresi_yalnizca_istenen_turu_dondurur(
    tmp_path: Path,
) -> None:
    depo = BacktestHistoryStore(tmp_path)
    depo.tek_hisse_kaydet(tek_hisse_sonucu())
    portfoy = depo.portfoy_kaydet(portfoy_sonucu())

    assert depo.kayitlari_listele(analiz_turu=PORTFOY_ANALIZI) == (
        portfoy,
    )


def test_dosya_baytlari_kayit_kimligiyle_de_okunur(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(tmp_path)
    kayit = depo.tek_hisse_kaydet(tek_hisse_sonucu())

    nesneyle = depo.dosya_baytlari(kayit, "islemler_csv")
    kimlikle = depo.dosya_baytlari(kayit.kayit_kimligi, "islemler_csv")

    assert kimlikle == nesneyle


def test_olmayan_dosya_turu_acik_hata_verir(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(tmp_path)
    kayit = depo.tek_hisse_kaydet(tek_hisse_sonucu())

    with pytest.raises(BacktestHistoryError, match="bulunamadı"):
        depo.dosya_baytlari(kayit, "bilinmeyen")


def test_bozuk_metadata_listelemeyi_durdurmaz(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(tmp_path)
    gecerli = depo.tek_hisse_kaydet(tek_hisse_sonucu())
    bozuk = tmp_path / "bozuk_kayit"
    bozuk.mkdir()
    (bozuk / METADATA_DOSYASI).write_text("{bozuk json", encoding="utf-8")

    assert depo.kayitlari_listele() == (gecerli,)


def test_kayit_limiti_pozitif_olmalidir(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(tmp_path)

    with pytest.raises(ValueError, match="pozitif"):
        depo.kayitlari_listele(limit=0)


def test_metadata_turkce_karakterlerle_kayipsiz_doner() -> None:
    kayit = BacktestHistoryRecord(
        kayit_kimligi="tek_hisse_123",
        analiz_turu=TEK_HISSE_ANALIZI,
        kaydedilme_zamani="2026-07-25T21:30:00+03:00",
        baslik="ŞİŞE.IS · Tek Hisse Backtest",
        semboller=("SISE.IS",),
        donem="2025-01-01 — 2026-01-01",
        tamamlanan_islem_sayisi=12,
        atlanan_islem_sayisi=3,
        bitis_sermayesi=125_000.0,
        toplam_getiri_yuzde=25.0,
        maksimum_dusus_yuzde=8.0,
        guncel_dusus_yuzde=1.0,
        kar_faktoru=1.5,
        kazanma_yuzde=58.0,
        ortalama_sermaye_kullanim_yuzde=None,
        maksimum_pozisyon=None,
        analiz_kimligi="analiz",
        veri_kimligi="veri",
        ayar_kimligi="ayar",
        dosyalar=(
            HistoryArtifact(
                tur="pdf",
                dosya_adi="ŞİŞE_rapor.pdf",
                mime="application/pdf",
                goreli_yol="ŞİŞE_rapor.pdf",
            ),
        ),
    )

    yeniden = BacktestHistoryRecord.sozlukten(
        json.loads(json.dumps(kayit.sozluk(), ensure_ascii=False))
    )

    assert yeniden == kayit


def test_dosya_yolu_kayit_klasoru_disina_cikamaz(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(tmp_path)
    kayit = depo.tek_hisse_kaydet(tek_hisse_sonucu())
    metadata_yolu = tmp_path / kayit.kayit_kimligi / METADATA_DOSYASI
    metadata = json.loads(metadata_yolu.read_text(encoding="utf-8"))
    metadata["dosyalar"][0]["goreli_yol"] = "../disarisi.csv"
    metadata_yolu.write_text(
        json.dumps(metadata, ensure_ascii=False),
        encoding="utf-8",
    )
    degistirilmis = depo.kayit_getir(kayit.kayit_kimligi)

    with pytest.raises(BacktestHistoryError, match="yolu geçersiz"):
        depo.dosya_baytlari(degistirilmis, "islemler_csv")


def test_kayit_sil_metadata_ve_raporlari_birlikte_kaldirir(
    tmp_path: Path,
) -> None:
    depo = BacktestHistoryStore(tmp_path)
    kayit = depo.tek_hisse_kaydet(tek_hisse_sonucu())
    klasor = tmp_path / kayit.kayit_kimligi

    silinen = depo.kayit_sil(kayit.kayit_kimligi)

    assert silinen == kayit
    assert not klasor.exists()
    assert depo.kayitlari_listele() == ()


def test_kayit_sil_diger_kayitlari_etkilemez(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(tmp_path)
    tek = depo.tek_hisse_kaydet(tek_hisse_sonucu())
    portfoy = depo.portfoy_kaydet(portfoy_sonucu())

    depo.kayit_sil(tek.kayit_kimligi)

    assert depo.kayitlari_listele() == (portfoy,)
    assert (tmp_path / portfoy.kayit_kimligi).is_dir()


def test_olmayan_kayit_silinemez(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(tmp_path)

    with pytest.raises(BacktestHistoryError, match="bulunamadı"):
        depo.kayit_sil("tek_hisse_olmayan")


def test_toplu_silme_secili_kayitlari_dondurur(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(tmp_path)
    tek = depo.tek_hisse_kaydet(tek_hisse_sonucu())
    portfoy = depo.portfoy_kaydet(portfoy_sonucu())

    silinenler = depo.kayitlari_sil(
        (tek.kayit_kimligi, portfoy.kayit_kimligi)
    )

    assert silinenler == (tek, portfoy)
    assert depo.kayitlari_listele() == ()
    assert tmp_path.is_dir()


def test_toplu_silme_tekrar_eden_kimligi_bir_kez_isler(
    tmp_path: Path,
) -> None:
    depo = BacktestHistoryStore(tmp_path)
    kayit = depo.tek_hisse_kaydet(tek_hisse_sonucu())

    silinenler = depo.kayitlari_sil(
        (kayit.kayit_kimligi, kayit.kayit_kimligi)
    )

    assert silinenler == (kayit,)
    assert depo.kayitlari_listele() == ()


def test_toplu_silme_bos_secimde_islem_yapmaz(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(tmp_path)
    kayit = depo.tek_hisse_kaydet(tek_hisse_sonucu())

    assert depo.kayitlari_sil(()) == ()
    assert depo.kayitlari_listele() == (kayit,)


def test_toplu_silme_tum_kayitlari_onceden_dogrular(tmp_path: Path) -> None:
    depo = BacktestHistoryStore(tmp_path)
    kayit = depo.tek_hisse_kaydet(tek_hisse_sonucu())

    with pytest.raises(BacktestHistoryError, match="bulunamadı"):
        depo.kayitlari_sil((kayit.kayit_kimligi, "tek_hisse_olmayan"))

    assert depo.kayitlari_listele() == (kayit,)
    assert (tmp_path / kayit.kayit_kimligi).is_dir()


def test_toplu_silme_duz_metin_yerine_koleksiyon_ister(
    tmp_path: Path,
) -> None:
    depo = BacktestHistoryStore(tmp_path)

    with pytest.raises(TypeError, match="koleksiyon"):
        depo.kayitlari_sil("tek_hisse_123")
