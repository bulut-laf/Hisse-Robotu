from backend.app.sector_analysis.sector_models import (
    SectorProfile,
)


def test_sector_profile_model():
    data = SectorProfile(
        name="Bankacılık",
        symbols=["AKBNK", "GARAN"],
    ).to_dict()

    assert data["name"] == "Bankacılık"
    assert "AKBNK" in data["symbols"]


def test_sector_model_has_no_trade_logic():
    data = SectorProfile(
        name="Sanayi",
    ).to_dict()

    assert "signal" not in data
    assert "buy" not in data
    assert "sell" not in data
