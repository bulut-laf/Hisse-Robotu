from datetime import date

import pytest

from backend.app.compliance.vbts_models import VbtsMeasure


def test_aktif_tedbir_bulunan_sembol_engellenir():
    from backend.app.compliance.vbts_guard import VbtsGuard

    guard = VbtsGuard(
        measures=[
            VbtsMeasure(
                symbol="EREGL",
                measure_type="BRUT_TAKAS",
                start_date=date(2026, 7, 20),
                end_date=date(2026, 8, 19),
                source="KAP",
                source_reference="bildirim-1",
            )
        ]
    )

    result = guard.evaluate(
        symbol="EREGL",
        control_date=date(2026, 7, 28),
    )

    assert result.is_allowed is False
    assert result.symbol == "EREGL.IS"
    assert result.active_measure_types == ("BRUT_TAKAS",)


def test_tedbir_suresi_dolmus_sembol_engellenmez():
    from backend.app.compliance.vbts_guard import VbtsGuard

    guard = VbtsGuard(
        measures=[
            VbtsMeasure(
                symbol="CCOLA",
                measure_type="TEK_FIYAT",
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 30),
                source="KAP",
                source_reference="bildirim-2",
            )
        ]
    )

    result = guard.evaluate(
        symbol="CCOLA.IS",
        control_date=date(2026, 7, 28),
    )

    assert result.is_allowed is True
    assert result.active_measure_types == ()


def test_ayni_sembolde_birden_fazla_aktif_tedbir_raporlanir():
    from backend.app.compliance.vbts_guard import VbtsGuard

    guard = VbtsGuard(
        measures=[
            VbtsMeasure(
                symbol="OYAKC",
                measure_type="BRUT_TAKAS",
                start_date=date(2026, 7, 1),
                end_date=date(2026, 8, 1),
                source="KAP",
                source_reference="bildirim-3",
            ),
            VbtsMeasure(
                symbol="OYAKC",
                measure_type="ACIGA_SATIS_YASAGI",
                start_date=date(2026, 7, 15),
                end_date=date(2026, 8, 15),
                source="KAP",
                source_reference="bildirim-4",
            ),
        ]
    )

    result = guard.evaluate(
        symbol="OYAKC",
        control_date=date(2026, 7, 28),
    )

    assert result.is_allowed is False
    assert result.active_measure_types == (
        "ACIGA_SATIS_YASAGI",
        "BRUT_TAKAS",
    )


def test_bos_sembol_reddedilir():
    from backend.app.compliance.vbts_guard import VbtsGuard

    guard = VbtsGuard(measures=[])

    with pytest.raises(ValueError):
        guard.evaluate(
            symbol=" ",
            control_date=date(2026, 7, 28),
        )