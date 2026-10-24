from pathlib import Path


def test_dashboard_gercek_sonuc_takibini_icerir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert 'st.markdown("Gerçek sonuç takibi")' in source
    assert "canli_sinyal_performansini_hesapla(" in source
    assert '"Canlı sonuçları CSV indir"' in source
    assert '"5G kapanış %"' not in source  # sütunlar vadeden dinamik üretilir
    assert 'suffix = f"{horizon.horizon}G"' in source
