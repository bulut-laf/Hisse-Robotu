from __future__ import annotations

import json

import pytest

from backend.app.data.fundamental_settings import (
    DEFAULT_FUNDAMENTAL_SETTINGS,
    FundamentalAnalysisSettings,
    FundamentalSettingsError,
    FundamentalSettingsJsonStore,
)


def test_varsayilan_ayarlar_guvenlidir():
    settings = DEFAULT_FUNDAMENTAL_SETTINGS

    assert settings.strong_threshold == 80
    assert settings.balanced_threshold == 65
    assert settings.watch_threshold == 50
    assert settings.minimum_sector_company_count == 3
    assert settings.sector_change_threshold == 3.0


def test_ayarlar_json_dosyasina_kaydedilir(tmp_path):
    store = FundamentalSettingsJsonStore(
        tmp_path / "settings.json"
    )
    settings = FundamentalAnalysisSettings(
        strong_threshold=85,
        balanced_threshold=70,
        watch_threshold=55,
        minimum_sector_company_count=4,
        sector_change_threshold=4.5,
        score_history_maximum_age_days=600,
        report_archive_maximum_age_days=900,
        default_archive_sort="score_desc",
    )

    store.save(settings)

    assert store.load() == settings


def test_ayar_dosyasi_yoksa_varsayilanlar_doner(tmp_path):
    store = FundamentalSettingsJsonStore(
        tmp_path / "missing.json"
    )

    assert store.load() == DEFAULT_FUNDAMENTAL_SETTINGS


def test_varsayilana_guvenli_donus_yapilir(tmp_path):
    store = FundamentalSettingsJsonStore(
        tmp_path / "settings.json"
    )
    store.save(
        FundamentalAnalysisSettings(
            strong_threshold=90,
            balanced_threshold=75,
            watch_threshold=60,
        )
    )

    result = store.reset()

    assert result == DEFAULT_FUNDAMENTAL_SETTINGS
    assert store.load() == DEFAULT_FUNDAMENTAL_SETTINGS


@pytest.mark.parametrize(
    "kwargs",
    (
        {
            "strong_threshold": 65,
            "balanced_threshold": 65,
            "watch_threshold": 50,
        },
        {
            "strong_threshold": 80,
            "balanced_threshold": 45,
            "watch_threshold": 50,
        },
        {"minimum_sector_company_count": 1},
        {"sector_change_threshold": 0},
        {"score_history_maximum_age_days": 10},
        {"report_archive_maximum_age_days": 10},
        {"default_archive_sort": "invalid"},
    ),
)
def test_gecersiz_ve_celisen_ayarlar_reddedilir(kwargs):
    with pytest.raises(FundamentalSettingsError):
        FundamentalAnalysisSettings(**kwargs)


def test_bozuk_json_ayar_dosyasi_reddedilir(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{bozuk", encoding="utf-8")
    store = FundamentalSettingsJsonStore(path)

    with pytest.raises(
        FundamentalSettingsError,
        match="okunamadı",
    ):
        store.load()
