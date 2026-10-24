from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.analysis.bist_universe import (
    EVREN_KODLARI,
    BistUniverseRepository,
    bist_bilesen_csvsini_ayristir,
)


def test_bist_50_resmi_endeks_koduyla_tanimlidir() -> None:
    assert EVREN_KODLARI["BIST 50"] == "XU050"


ORNEK_CSV = """BILESEN KODU;BULTEN_ADI;ENDEKS KODU;ENDEKS ADI;ENDEKS INGILIZCE ADI;TARIH(GG/AA/YYYY)\nCONSTITUENT CODE;CONSTITUENT NAME;INDEX CODE;INDEX NAME IN TURKISH;INDEX NAME IN ENGLISH;DATE(DD/MM/YYYY)\nTHYAO.E;TURK HAVA YOLLARI;XU100;BIST 100;BIST 100;27/07/2026\nASELS.E;ASELSAN;XU100;BIST 100;BIST 100;27/07/2026\nTHYAO.E;TURK HAVA YOLLARI;XU030;BIST 30;BIST 30;27/07/2026\n"""


def test_bist_csv_sembolleri_yahoo_bicimine_donusturur() -> None:
    evren = bist_bilesen_csvsini_ayristir(
        ORNEK_CSV,
        evren_adi="BIST 100",
        endeks_kodu="XU100",
        kaynak="Test",
        resmi_kaynaktan_guncel=True,
    )

    assert evren.semboller == ("THYAO.IS", "ASELS.IS")
    assert evren.tarih == "27/07/2026"
    assert evren.sembol_sayisi == 2
    assert evren.resmi_kaynaktan_guncel is True


def test_repository_resmi_kaynagi_kullanir_ve_onbellege_yazar(
    tmp_path: Path,
) -> None:
    onbellek = tmp_path / "cache" / "bist.csv"
    snapshot = tmp_path / "snapshot.csv"
    snapshot.write_text(ORNEK_CSV, encoding="utf-8")

    depo = BistUniverseRepository(
        snapshot_yolu=snapshot,
        onbellek_yolu=onbellek,
        indirici=lambda _url: ORNEK_CSV.encode("utf-8"),
    )

    evren = depo.evreni_yukle("BIST 100")

    assert evren.kaynak == "Borsa İstanbul güncel CSV"
    assert onbellek.read_bytes() == ORNEK_CSV.encode("utf-8")


def test_repository_ag_hatasinda_snapshot_kullanir(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.csv"
    snapshot.write_text(ORNEK_CSV, encoding="utf-8")

    def hata_ver(_url: str) -> bytes:
        raise OSError("ağ yok")

    depo = BistUniverseRepository(
        snapshot_yolu=snapshot,
        onbellek_yolu=tmp_path / "yok.csv",
        indirici=hata_ver,
    )

    evren = depo.evreni_yukle("BIST 30")

    assert evren.semboller == ("THYAO.IS",)
    assert evren.kaynak == "Paketlenmiş BIST anlık görüntüsü"
    assert evren.resmi_kaynaktan_guncel is False


def test_bilinmeyen_evren_reddedilir(tmp_path: Path) -> None:
    depo = BistUniverseRepository(snapshot_yolu=tmp_path / "x.csv")

    with pytest.raises(ValueError, match="Bilinmeyen BIST evreni"):
        depo.evreni_yukle("BIST 42", internetten_guncelle=False)
