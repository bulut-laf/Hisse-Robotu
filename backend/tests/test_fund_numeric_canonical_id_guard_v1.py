import pytest

from backend.app.funds.contracts import _fund_id


def test_numeric_tefas_canonical_id_is_rejected():
    with pytest.raises(
        ValueError,
        match="INVALID_NUMERIC_TEFAS_FUND_ID",
    ):
        _fund_id("fund:tefas:370001")


def test_normal_tefas_canonical_id_is_preserved():
    assert _fund_id("fund:tefas:KHA") == "fund:tefas:KHA"
