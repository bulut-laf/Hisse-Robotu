from pathlib import Path


def test_dashboard_canli_izleme_portfoyunu_icerir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert "canli_sinyalleri_kaydet(" in source
    assert '"Canlı İzleme Portföyü"' in source
    assert '"E2–E4 adaylarını canlı izlemeye kaydet"' in source
    assert "mode == \"Güncel hazırlık\"" in source
