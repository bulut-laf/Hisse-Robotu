\
from backend.app.market_context.store import MarketContextStore


def test_duplicate_hash_ignores_line_ending_difference():
    a = MarketContextStore.content_hash(
        "Endeks pozitif.\r\nDestek 13.200"
    )
    b = MarketContextStore.content_hash(
        "Endeks pozitif.\nDestek 13.200"
    )

    assert a == b


def test_duplicate_hash_distinguishes_different_content():
    a = MarketContextStore.content_hash(
        "Endeks pozitif."
    )
    b = MarketContextStore.content_hash(
        "Endeks negatif."
    )

    assert a != b
