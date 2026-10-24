from backend.app.funds.ui_live_refresh import refresh_fund_analysis_if_requested


def test_initial_entry_does_not_call_live_provider():
    calls = []

    def forbidden_loader():
        calls.append("called")
        raise AssertionError("LIVE_PROVIDER_CALLED_ON_ENTRY")

    outcome = refresh_fund_analysis_if_requested(
        requested=False,
        current_results=(),
        loader=forbidden_loader,
    )

    assert calls == []
    assert outcome.results == ()
    assert outcome.refreshed is False
    assert outcome.error_message is None


def test_explicit_refresh_calls_provider_once_and_replaces_results():
    expected = object()
    calls = []

    def loader():
        calls.append("called")
        return (expected,)

    outcome = refresh_fund_analysis_if_requested(
        requested=True,
        current_results=(),
        loader=loader,
    )

    assert calls == ["called"]
    assert outcome.results == (expected,)
    assert outcome.refreshed is True
    assert outcome.error_message is None


def test_failed_refresh_preserves_last_good_results():
    previous = object()

    def failing_loader():
        raise RuntimeError("TEFAS_DOWN")

    outcome = refresh_fund_analysis_if_requested(
        requested=True,
        current_results=(previous,),
        loader=failing_loader,
    )

    assert outcome.results == (previous,)
    assert outcome.refreshed is False
    assert outcome.error_message == "TEFAS_DOWN"
