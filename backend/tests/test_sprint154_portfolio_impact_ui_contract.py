from pathlib import Path

UI = Path("backend/app/ui/news_center_dashboard.py")
MODULE = Path("backend/app/news_center/portfolio_impact.py")


def _source(path=UI) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_sprint154_golge_portfoy_yalniz_acik_pozisyonlari_okur():
    source = _source()
    assert "ShadowPortfolioStore" in source
    assert "OPEN_STATUS" in source
    assert "item.status == OPEN_STATUS" in source


def test_sprint154_portfoy_etki_radari_uiya_baglanir():
    source = _source()
    assert '"Portföy Etki Radarı"' in source
    assert "build_portfolio_impact_radar" in source
    assert "portfolio_symbol_summary_rows" in source
    assert "portfolio_impact_rows" in source


def test_sprint154_oncelik_kurali_kullaniciya_aciklanir():
    source = _source()
    assert "Öncelik:" in source
    assert "DIRECT_SYMBOL" in source
    assert "SECTOR" in source
    assert "MARKET" in source
    assert "tek satır gösterilir" in source


def test_portfoy_radari_teknik_karar_ve_fiyat_yonu_uretmez():
    source = _source(MODULE).casefold()
    forbidden = (
        "technical_score =",
        "buy_signal",
        "sell_signal",
        "price_direction",
        "target_price",
    )
    for token in forbidden:
        assert token not in source
    assert "fiyat\n    yönü" in source or "fiyat yönü" in source
