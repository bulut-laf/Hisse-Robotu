from __future__ import annotations

from backend.app import opportunity_radar as radar


def test_monthly_validation_artifacts_are_installed() -> None:
    assert radar.MONTHLY_QUANTILE_FILE.exists()
    assert radar.MONTHLY_PASSED_PROFILE_FILE.exists()


def test_monthly_validation_profiles_have_passed_rows() -> None:
    edges, profiles = radar._load_monthly_validated_profiles()
    assert not edges.empty
    assert not profiles.empty
    assert set(profiles["monthly_class"]) <= {"GUCLU_TREND", "ERKEN_TREND"}


def test_monthly_profile_status_precedence() -> None:
    current = {
        "snapshot": "CURRENT_PARTIAL",
        "matches": [{"quality": 19.59, "profile": "P1", "excess3": 3.37, "excess6": 14.86}],
    }
    closed = {
        "snapshot": "LAST_CLOSED",
        "matches": [{"quality": 14.68, "profile": "P2", "excess3": 5.69, "excess6": 6.92}],
    }
    status = radar._monthly_profile_status(current, closed)
    assert status["Durum"] == "Ay İçi Geçici Match"
    assert status["Profile Match Count"] == 1

    status = radar._monthly_profile_status(
        {"snapshot": "CURRENT_PARTIAL", "matches": []},
        closed,
    )
    assert status["Durum"] == "Validated Profile Match"
    assert status["Profile Match Count"] == 1


def test_monthly_profile_no_match_contract() -> None:
    status = radar._monthly_profile_status(
        {"snapshot": "CURRENT_PARTIAL", "matches": []},
        {"snapshot": "LAST_CLOSED", "matches": []},
    )
    assert status["Durum"] == "Henüz Validate Değil"
    assert status["Profile Match Count"] == 0
