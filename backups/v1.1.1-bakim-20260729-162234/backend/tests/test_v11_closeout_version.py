from pathlib import Path

from backend.app.diagnostics.system_check import SISTEM_KONTROL_SURUMU


PROJE_KOKU = Path(__file__).resolve().parents[2]


def test_v11_surum_dosyasi_ve_sistem_kontrolu_uyumludur() -> None:
    assert (PROJE_KOKU / "VERSION").read_text(encoding="utf-8").strip() == "1.1.0"
    assert SISTEM_KONTROL_SURUMU == "V1.1"
