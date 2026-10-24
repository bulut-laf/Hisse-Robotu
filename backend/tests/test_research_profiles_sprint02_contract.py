from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_market_scan_result_exposes_same_successful_scan_without_second_scanner():
    text = (ROOT / "backend/app/analysis/market_scanner.py").read_text(encoding="utf-8")
    assert "RPV1_SPRINT02_SUCCESSFUL_RESULTS" in text
    assert "tum_sonuclar=tuple(tarama.basarili_sonuclar)" in text
    assert "BistMarketScannerService" in text


def test_dashboard_has_research_profiles_daily_bundle_and_panel():
    text = (ROOT / "backend/dashboard.py").read_text(encoding="utf-8")
    assert "RPV1_SPRINT02_DASHBOARD_IMPORT" in text
    assert "RPV1_SPRINT02_BUILD_BUNDLE" in text
    assert "RPV1_SPRINT02_RENDER_PANEL" in text
    assert "research_profiles_bundle=research_profiles_bundle" in text


def test_dashboard_research_profiles_uses_same_scan_successful_results():
    text = (ROOT / "backend/dashboard.py").read_text(encoding="utf-8")
    assert 'getattr(sonuc, "tum_sonuclar", ())' in text
    assert "build_daily_research_profiles(" in text
    assert "Research Profiles" not in text or "render_research_profiles_panel" in text


def test_research_profiles_has_no_new_store_or_trade_authority():
    daily = (ROOT / "backend/app/analysis/research_profiles_daily.py").read_text(encoding="utf-8")
    ui = (ROOT / "backend/app/ui/research_profiles_dashboard.py").read_text(encoding="utf-8")
    joined = (daily + "\n" + ui).lower()
    assert "jsonlstore" not in joined
    assert "sqlite" not in joined
    assert "trade_decision" not in joined
    assert "position_size" not in joined
    assert "al_sat" not in joined
