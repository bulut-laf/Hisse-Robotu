from pathlib import Path
import ast
import re


DASHBOARD = Path("backend/dashboard.py")
LABEL = "Piyasa Haber, Olay ve Etki Merkezi"


def _source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def _analysis_modes() -> tuple[str, ...]:
    tree = ast.parse(_source())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "ANALIZ_MODLARI"
                for target in node.targets
            ):
                value = ast.literal_eval(node.value)
                assert isinstance(value, tuple)
                return value
    raise AssertionError("ANALIZ_MODLARI bulunamadı.")


def _turkish_sort_key(value: str):
    alphabet = "abcçdefgğhıijklmnoöprsştuüvyz"
    order = {char: index for index, char in enumerate(alphabet)}
    normalized = value.casefold().replace("i̇", "i")
    return tuple(order.get(char, 1000 + ord(char)) for char in normalized)


def test_news_center_dashboard_import_edilir():
    assert (
        "from backend.app.ui.news_center_dashboard import "
        "render_news_center_dashboard"
    ) in _source()


def test_news_center_analiz_menusunde_ve_alfabetik():
    modes = _analysis_modes()
    assert LABEL in modes
    assert modes == tuple(sorted(modes, key=_turkish_sort_key))


def test_news_center_dedicated_route_kullanir():
    source = _source()
    assert f'elif analiz_modu == "{LABEL}":' in source
    assert "render_news_center_dashboard(st)" in source


def test_news_center_route_teknik_karar_motoruna_dokunmaz():
    source = _source()
    route_match = re.search(
        rf'elif analiz_modu == "{re.escape(LABEL)}":'
        r"(?P<body>.*?)(?=^    elif analiz_modu == |^    else:)",
        source,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert route_match is not None

    body = route_match.group("body").casefold()
    forbidden = (
        "technical_score",
        "candidate_rank",
        "buy_signal",
        "sell_signal",
        "risk_engine",
        "signal_engine",
        "market_scanner",
    )
    for token in forbidden:
        assert token not in body
