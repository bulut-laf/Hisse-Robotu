from backend.app.analysis.bist_daily_market import (
    bist_tum_sirket_adlarini_yukle,
    sembol_eslesmeleri,
)


def test_company_name_matching_preserves_symbol_priority():
    universe = ["AKBNK.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS"]
    names = {
        "AKBNK": "AKBANK",
        "AKSA": "AKSA",
        "AKSEN": "AKSA ENERJI",
        "ALARK": "ALARKO HOLDING",
    }
    assert sembol_eslesmeleri("AKBNK", universe, company_names=names) == ["AKBNK"]
    assert sembol_eslesmeleri("AK", universe, company_names=names) == ["AKBNK", "AKSA", "AKSEN"]


def test_company_name_matching_falls_back_to_official_name():
    universe = ["AKBNK.IS", "ALARK.IS"]
    names = {"AKBNK": "AKBANK", "ALARK": "ALARKO HOLDING"}
    assert sembol_eslesmeleri("AKBANK", universe, company_names=names) == ["AKBNK"]
    assert sembol_eslesmeleri("ALARKO", universe, company_names=names) == ["ALARK"]


def test_existing_official_metadata_loader_reuses_project_csv():
    names = bist_tum_sirket_adlarini_yukle()
    assert names
    assert names.get("AKBNK") == "AKBANK"
    assert names.get("ALARK") == "ALARKO HOLDING"
