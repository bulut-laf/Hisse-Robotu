from __future__ import annotations

from backend.app.funds.international.erste_hungary_universe import (
    build_unfiltered_form,
    parse_slider_bounds,
    parse_universe_list_html,
)


def test_slider_bounds_are_read_from_search_page():
    html = """
    <input id="returnSlider-input" data-min-max="-25,180" value="-25,180" />
    """
    assert parse_slider_bounds(html) == (-25, 180)


def test_unfiltered_form_uses_real_slider_bounds():
    assert build_unfiltered_form(ret_min=-25, ret_max=180) == [
        ("keyword", ""),
        ("segment", ""),
        ("ret_min", "-25"),
        ("ret_max", "180"),
    ]


def test_universe_parser_extracts_isin_and_detail_links():
    html = """
    <a href="/befektetesi_alapok/alap/HU0000704200">Fund A</a>
    <a href="/befektetesi_alapok/alap/AT0000A07HF4">Fund B</a>
    """
    result = parse_universe_list_html(
        html,
        total_count=2,
        ret_min=-25,
        ret_max=180,
    )

    assert result.total_count == 2
    assert result.isins == (
        "AT0000A07HF4",
        "HU0000704200",
    )
    assert result.detail_urls == (
        "https://www.erstemarket.hu/befektetesi_alapok/alap/AT0000A07HF4",
        "https://www.erstemarket.hu/befektetesi_alapok/alap/HU0000704200",
    )


def test_universe_parser_falls_back_to_embedded_isin():
    html = '<div data-isin="LU0123456789"></div>'
    result = parse_universe_list_html(
        html,
        total_count=1,
        ret_min=0,
        ret_max=100,
    )
    assert result.isins == ("LU0123456789",)
    assert result.detail_urls == ()

def test_appvars_path_is_extracted_from_object_literal():
    from backend.app.funds.international.erste_hungary_universe import (
        parse_app_base_path,
    )

    html = """
    <script>
    var appVars = {
        path: "/erstemarket/web/site/",
        language: "hu"
    };
    </script>
    """

    assert parse_app_base_path(html) == "/erstemarket/web/site/"


def test_appvars_path_is_extracted_from_assignment():
    from backend.app.funds.international.erste_hungary_universe import (
        parse_app_base_path,
    )

    html = """<script>appVars.path='/app/base';</script>"""
    assert parse_app_base_path(html) == "/app/base/"


def test_endpoints_are_built_from_appvars_path():
    from backend.app.funds.international.erste_hungary_universe import (
        build_endpoints,
    )

    list_url, count_url = build_endpoints("/erstemarket/web/site/")

    assert list_url == (
        "https://www.erstemarket.hu/erstemarket/web/site/"
        "funds/search_results/list?layout=website"
    )
    assert count_url == (
        "https://www.erstemarket.hu/erstemarket/web/site/"
        "funds/search_results/count"
    )

def test_page_endpoint_contract_matches_frontend():
    from backend.app.funds.international.erste_hungary_universe import (
        build_page_endpoint,
    )

    assert build_page_endpoint("/", page=1) == (
        "https://www.erstemarket.hu/funds/search_results/list?layout=website"
    )
    assert build_page_endpoint("/", page=2) == (
        "https://www.erstemarket.hu/funds/search_results/list/page:2?layout=website"
    )
    assert build_page_endpoint("/", page=63) == (
        "https://www.erstemarket.hu/funds/search_results/list/page:63?layout=website"
    )


def test_extract_isins_and_urls_deduplicates():
    from backend.app.funds.international.erste_hungary_universe import (
        extract_isins_and_detail_urls,
    )

    html = """
    <a href="/befektetesi_alapok/alap/HU0000716402">A</a>
    <a href="/befektetesi_alapok/alap/HU0000716402">A again</a>
    <a href="/befektetesi_alapok/alap/LU0123456789">B</a>
    """

    isins, urls = extract_isins_and_detail_urls(html)

    assert isins == ("HU0000716402", "LU0123456789")
    assert len(urls) == 2