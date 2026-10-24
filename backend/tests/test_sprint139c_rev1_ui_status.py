import ast
from pathlib import Path


def test_ai_status_is_updated_after_success_before_metric_render():
    path = Path("backend/app/ui/market_context_dashboard.py")
    source = path.read_text(encoding="utf-8")

    success_update = 'ai_review_status = "reviewed"'
    status_metric = 'c2.metric("AI durumu", status_text)'

    assert success_update in source
    assert status_metric in source
    assert source.index(success_update) < source.index(status_metric)


def test_ai_ui_does_not_call_streamlit_rerun():
    path = Path("backend/app/ui/market_context_dashboard.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func
        if not isinstance(func, ast.Attribute):
            continue

        assert not (
            isinstance(func.value, ast.Name)
            and func.value.id == "st"
            and func.attr == "rerun"
        )
