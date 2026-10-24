from datetime import date

import pytest


def test_vbts_tedbiri_sembol_ve_tarih_araligini_saklar():
    from backend.app.compliance.vbts_models import VbtsMeasure

    tedbir = VbtsMeasure(
        symbol="EREGL",
        measure_type="BRUT_TAKAS",
        start_date=date(2026, 7, 20),
        end_date=date(2026, 8, 19),
        source="KAP",
        source_reference="ornek-bildirim",
    )

    assert tedbir.symbol == "EREGL.IS"
    assert tedbir.is_active_on(date(2026, 7, 28)) is True
    assert tedbir.is_active_on(date(2026, 8, 20)) is False


def test_bitis_tarihi_bilinmeyen_tedbir_guvenli_kabul_edilmez():
    from backend.app.compliance.vbts_models import VbtsMeasure

    with pytest.raises(ValueError):
        VbtsMeasure(
            symbol="CCOLA",
            measure_type="BRUT_TAKAS",
            start_date=date(2026, 7, 20),
            end_date=None,
            source="KAP",
            source_reference="eksik-bildirim",
        )


def test_gecersiz_tarih_araligi_reddedilir():
    from backend.app.compliance.vbts_models import VbtsMeasure

    with pytest.raises(ValueError):
        VbtsMeasure(
            symbol="OYAKC",
            measure_type="TEK_FIYAT",
            start_date=date(2026, 8, 10),
            end_date=date(2026, 8, 1),
            source="KAP",
            source_reference="gecersiz-bildirim",
        )

