from __future__ import annotations

from backend.app.funds.international.erste_hungary_endpoint_discovery import (
    discover_endpoint_candidates,
)


def test_endpoint_discovery_extracts_relevant_strings():
    javascript = r"""
    function loadFunds() {
        return $.ajax({
            url: "/ajax/befektetesi_alapok/kereses",
            type: "POST"
        });
    }
    const other = "/api/funds/list";
    const noise = "/images/logo.svg";
    """

    result = discover_endpoint_candidates(javascript)

    assert "/ajax/befektetesi_alapok/kereses" in result.string_candidates
    assert "/api/funds/list" in result.string_candidates
    assert "/images/logo.svg" not in result.string_candidates
    assert (
        "https://www.erstemarket.hu/ajax/befektetesi_alapok/kereses"
        in result.absolute_url_candidates
    )


def test_endpoint_discovery_collects_http_call_context():
    javascript = """
    var settings = { category: 'all' };
    $.ajax({
        url: '/funds/search',
        method: 'POST',
        data: settings
    });
    """

    result = discover_endpoint_candidates(javascript)

    assert result.call_snippets
    assert any("/funds/search" in item for item in result.call_snippets)


def test_endpoint_discovery_is_deterministic():
    javascript = 'var a="/api/funds"; var b="/api/funds";'
    result = discover_endpoint_candidates(javascript)
    assert result.string_candidates == ("/api/funds",)