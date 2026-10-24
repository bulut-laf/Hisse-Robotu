from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "backend.run_system_check",
    "Güncel Teknik Analiz",
    "BIST Toplu Tarama",
    "Açık Pozisyon İzleme",
    "İşlem Kayıp Analizi",
    "Analiz Geçmişi",
)


def test_v11_kullanim_kilavuzlari_ana_akislari_icerir() -> None:
    for relative_path in ("KULLANIM.md", "KULLANIM_KILAVUZU.md"):
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        missing = [item for item in REQUIRED if item not in content]
        assert not missing, f"{relative_path} eksik ifadeler: {missing}"
