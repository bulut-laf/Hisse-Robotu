from pathlib import Path


def test_daily_operation_kok_neden_teshisini_kaydeder():
    source=Path('backend/app/prebreakout/prebreakout_daily_operation.py').read_text(encoding='utf-8')
    assert 'operasyon_kok_nedenini_teshis_et(' in source
    assert 'operasyon_teshisini_kaydet(' in source
    assert 'diagnosis_path:' in source
