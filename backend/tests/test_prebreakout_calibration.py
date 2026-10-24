import pandas as pd
import pytest

from backend.app.prebreakout.prebreakout_calibration import (
    ThresholdCalibrationConfig,
    compare_thresholds,
    generate_calibration_report,
)


def records_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "score": [35, 40, 44, 45, 46, 49, 50, 52, 55, 58, 60, 65],
            "performance_label": [
                "Yanlış pozitif",
                "Sınırlı hareket",
                "Yanlış pozitif",
                "Yanlış pozitif",
                "Sınırlı hareket",
                "Başarılı",
                "Başarılı",
                "Başarılı",
                "Başarılı",
                "Başarılı",
                "Başarılı",
                "Başarılı",
            ],
        }
    )


def test_esikler_deterministik_ve_mevcut_esikle_birlikte_karsilastirilir() -> None:
    config = ThresholdCalibrationConfig(
        current_threshold=45,
        alternative_thresholds=(55, 40, 50, 40),
        minimum_sample_size=2,
    )

    result = compare_thresholds(records_table(), config)

    assert result["threshold"].tolist() == [40, 45, 50, 55]
    assert result["is_current"].sum() == 1
    assert result.loc[result["threshold"] == 50, "sample_count"].iloc[0] == 6


def test_rapor_uygun_alternatifi_onerir_ama_otomatik_degistirmez() -> None:
    config = ThresholdCalibrationConfig(
        current_threshold=45,
        alternative_thresholds=(50, 55),
        minimum_sample_size=3,
        minimum_coverage_pct=50.0,
        minimum_quality_gain=3.0,
    )

    report = generate_calibration_report(records_table(), config)

    assert report.recommendation.recommended_threshold in (50, 55)
    assert report.recommendation.automatic_change_applied is False
    assert "otomatik" in report.recommendation.reason.lower()


def test_yetersiz_orneklemde_mevcut_esik_korunur() -> None:
    config = ThresholdCalibrationConfig(
        current_threshold=45,
        alternative_thresholds=(50,),
        minimum_sample_size=100,
    )

    report = generate_calibration_report(records_table(), config)

    assert report.recommendation.recommended_threshold == 45
    assert report.recommendation.decision == "Yetersiz örneklem"


def test_bos_veri_guvenli_rapor_uretir() -> None:
    report = generate_calibration_report(
        pd.DataFrame(),
        ThresholdCalibrationConfig(),
    )

    assert report.comparison.empty
    assert report.recommendation.decision == "Yetersiz veri"


def test_eksik_sutun_reddedilir() -> None:
    with pytest.raises(ValueError, match="performance_label"):
        compare_thresholds(
            pd.DataFrame({"score": [45]}),
            ThresholdCalibrationConfig(),
        )


def test_gecersiz_esik_reddedilir() -> None:
    with pytest.raises(ValueError):
        ThresholdCalibrationConfig(current_threshold=101)

