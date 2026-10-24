from __future__ import annotations

import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from backend.app.history.backtest_history import (
    METADATA_DOSYASI,
    BacktestHistoryStore,
)
from backend.app.history.backtest_history_backup import (
    MANIFEST_DOSYASI,
    BacktestHistoryBackupError,
    BacktestHistoryBackupService,
)
from backend.tests.test_report_export import (
    portfoy_sonucu,
    tek_hisse_sonucu,
)


def _zip_entries(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
        return {
            info.filename: archive.read(info.filename)
            for info in archive.infolist()
            if not info.is_dir()
        }


def _zip_from_entries(entries: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return output.getvalue()


def _two_records(store: BacktestHistoryStore):
    first = store.tek_hisse_kaydet(tek_hisse_sonucu())
    original = tek_hisse_sonucu()
    second_summary = replace(
        original.ozet,
        analiz_kimligi="ikinci-analiz",
        veri_kimligi="ikinci-veri",
    )
    second = store.tek_hisse_kaydet(replace(original, ozet=second_summary))
    return first, second


def test_yedek_manifest_metadata_ve_raporlari_icerir(tmp_path: Path) -> None:
    store = BacktestHistoryStore(tmp_path)
    record = store.tek_hisse_kaydet(tek_hisse_sonucu())
    service = BacktestHistoryBackupService(store)

    backup = service.yedek_olustur()
    entries = _zip_entries(backup)
    manifest = json.loads(entries[MANIFEST_DOSYASI].decode("utf-8"))

    assert manifest["surum"] == 1
    assert manifest["kayit_sayisi"] == 1
    assert f"kayitlar/{record.kayit_kimligi}/{METADATA_DOSYASI}" in entries
    assert any(name.endswith(".csv") for name in entries)
    assert any(name.endswith(".pdf") for name in entries)


def test_secili_kayitlar_yedeklenir(tmp_path: Path) -> None:
    store = BacktestHistoryStore(tmp_path)
    first, second = _two_records(store)
    service = BacktestHistoryBackupService(store)

    preview = service.yedegi_incele(
        service.yedek_olustur((second.kayit_kimligi,))
    )

    assert preview.toplam_kayit == 1
    assert preview.kayit_kimlikleri == (second.kayit_kimligi,)
    assert first.kayit_kimligi not in preview.kayit_kimlikleri


def test_yedek_bos_gecmiste_gecerli_manifest_uretir(tmp_path: Path) -> None:
    service = BacktestHistoryBackupService(BacktestHistoryStore(tmp_path))

    backup = service.yedek_olustur()
    preview = service.yedegi_incele(backup)
    result = service.yedegi_geri_yukle(backup)

    assert preview.toplam_kayit == 0
    assert preview.yeni_kayit == 0
    assert result.geri_yuklenen == 0
    assert result.toplam_kayit == 0


def test_yedek_bos_depo_uzerine_tam_geri_yuklenir(tmp_path: Path) -> None:
    source = BacktestHistoryStore(tmp_path / "source")
    first, second = _two_records(source)
    backup = BacktestHistoryBackupService(source).yedek_olustur()
    target = BacktestHistoryStore(tmp_path / "target")
    service = BacktestHistoryBackupService(target)

    preview = service.yedegi_incele(backup)
    result = service.yedegi_geri_yukle(backup)

    assert preview.yeni_kayit == 2
    assert result.geri_yuklenen == 2
    assert {item.kayit_kimligi for item in target.kayitlari_listele()} == {
        first.kayit_kimligi,
        second.kayit_kimligi,
    }


def test_ayni_kayit_geri_yuklemede_atlanir(tmp_path: Path) -> None:
    store = BacktestHistoryStore(tmp_path)
    store.tek_hisse_kaydet(tek_hisse_sonucu())
    service = BacktestHistoryBackupService(store)
    backup = service.yedek_olustur()

    preview = service.yedegi_incele(backup)
    result = service.yedegi_geri_yukle(backup)

    assert preview.yeni_kayit == 0
    assert preview.zaten_mevcut == 1
    assert result.geri_yuklenen == 0
    assert result.atlanan_ayni_kayit == 1


def test_tek_hisse_ve_portfoy_birlikte_geri_yuklenir(tmp_path: Path) -> None:
    source = BacktestHistoryStore(tmp_path / "source")
    source.tek_hisse_kaydet(tek_hisse_sonucu())
    source.portfoy_kaydet(portfoy_sonucu())
    backup = BacktestHistoryBackupService(source).yedek_olustur()
    target = BacktestHistoryStore(tmp_path / "target")

    result = BacktestHistoryBackupService(target).yedegi_geri_yukle(backup)

    assert result.geri_yuklenen == 2
    assert {record.analiz_turu for record in target.kayitlari_listele()} == {
        "tek_hisse",
        "portfoy",
    }


def test_gecersiz_zip_acik_hata_verir(tmp_path: Path) -> None:
    service = BacktestHistoryBackupService(BacktestHistoryStore(tmp_path))

    with pytest.raises(BacktestHistoryBackupError, match="Geçerli"):
        service.yedegi_incele("zip değil".encode("utf-8"))


def test_desteklenmeyen_manifest_surumu_reddedilir(tmp_path: Path) -> None:
    entries = {
        MANIFEST_DOSYASI: json.dumps(
            {"surum": 99, "kayit_sayisi": 0, "kayitlar": []}
        ).encode("utf-8")
    }
    service = BacktestHistoryBackupService(BacktestHistoryStore(tmp_path))

    with pytest.raises(BacktestHistoryBackupError, match="sürümü"):
        service.yedegi_incele(_zip_from_entries(entries))


def test_zip_yol_gecisi_reddedilir(tmp_path: Path) -> None:
    entries = {
        MANIFEST_DOSYASI: json.dumps(
            {"surum": 1, "kayit_sayisi": 0, "kayitlar": []}
        ).encode("utf-8"),
        "../disari.txt": b"tehlikeli",
    }
    service = BacktestHistoryBackupService(BacktestHistoryStore(tmp_path))

    with pytest.raises(BacktestHistoryBackupError, match="güvenli olmayan"):
        service.yedegi_incele(_zip_from_entries(entries))


def test_hashi_degisik_rapor_reddedilir(tmp_path: Path) -> None:
    store = BacktestHistoryStore(tmp_path)
    store.tek_hisse_kaydet(tek_hisse_sonucu())
    service = BacktestHistoryBackupService(store)
    entries = _zip_entries(service.yedek_olustur())
    report_path = next(name for name in entries if name.endswith(".csv"))
    entries[report_path] += b"bozuldu"

    with pytest.raises(BacktestHistoryBackupError, match="doğrulanamadı"):
        service.yedegi_incele(_zip_from_entries(entries))


def test_beklenmeyen_ek_dosya_reddedilir(tmp_path: Path) -> None:
    store = BacktestHistoryStore(tmp_path)
    store.tek_hisse_kaydet(tek_hisse_sonucu())
    service = BacktestHistoryBackupService(store)
    entries = _zip_entries(service.yedek_olustur())
    entries["fazladan.txt"] = b"fazla"

    with pytest.raises(BacktestHistoryBackupError, match="beklenmeyen"):
        service.yedegi_incele(_zip_from_entries(entries))


def test_ayni_kimlikte_farkli_mevcut_kayit_geri_yuklemeyi_durdurur(
    tmp_path: Path,
) -> None:
    source = BacktestHistoryStore(tmp_path / "source")
    record = source.tek_hisse_kaydet(tek_hisse_sonucu())
    backup = BacktestHistoryBackupService(source).yedek_olustur()

    target = BacktestHistoryStore(tmp_path / "target")
    target_record = target.tek_hisse_kaydet(tek_hisse_sonucu())
    metadata_path = (
        target.kok_klasor / target_record.kayit_kimligi / METADATA_DOSYASI
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["kaydedilme_zamani"] = "2099-01-01T00:00:00+03:00"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False),
        encoding="utf-8",
    )
    service = BacktestHistoryBackupService(target)

    with pytest.raises(BacktestHistoryBackupError, match="farklı"):
        service.yedegi_geri_yukle(backup)

    assert (target.kok_klasor / record.kayit_kimligi).is_dir()
    assert len(target.kayitlari_listele()) == 1
