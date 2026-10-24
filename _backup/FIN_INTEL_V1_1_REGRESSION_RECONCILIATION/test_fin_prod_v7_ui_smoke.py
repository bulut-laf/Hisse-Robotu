
from __future__ import annotations

from pathlib import Path
import importlib.util
import json
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
UI = BACKEND / "app" / "ui" / "financial_intelligence_dashboard.py"
PANEL = BACKEND / "data" / "financial_intelligence" / "TUPRS_financial_intelligence_panel.json"
DASHBOARD = BACKEND / "dashboard.py"


class _Ctx:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


class _MetricSink:
    def __init__(self, calls):
        self.calls = calls
    def metric(self, label, value, *args, **kwargs):
        self.calls.append(("metric", label, value))


class FakeStreamlit:
    def __init__(self):
        self.calls = []
    def markdown(self, *args, **kwargs): self.calls.append(("markdown", args[0] if args else ""))
    def caption(self, *args, **kwargs): self.calls.append(("caption", args[0] if args else ""))
    def info(self, *args, **kwargs): self.calls.append(("info", args[0] if args else ""))
    def warning(self, *args, **kwargs): self.calls.append(("warning", args[0] if args else ""))
    def error(self, *args, **kwargs): self.calls.append(("error", args[0] if args else ""))
    def success(self, *args, **kwargs): self.calls.append(("success", args[0] if args else ""))
    def write(self, *args, **kwargs): self.calls.append(("write", *args))
    def dataframe(self, *args, **kwargs): self.calls.append(("dataframe",))
    def divider(self): self.calls.append(("divider",))
    def text_input(self, label, value="", **kwargs):
        self.calls.append(("text_input", label, value))
        return value
    def columns(self, n):
        return [_MetricSink(self.calls) for _ in range(n)]
    def tabs(self, labels):
        self.calls.append(("tabs", tuple(labels)))
        return [_Ctx() for _ in labels]


def _load_ui():
    spec = importlib.util.spec_from_file_location("fin_ui_smoke", UI)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_financial_intelligence_renderer_smoke_real_tuprs_artifact():
    assert PANEL.exists(), PANEL
    payload = json.loads(PANEL.read_text(encoding="utf-8-sig"))
    assert payload["status"] == "PASS"
    assert payload["sections"]["coverage_readiness"]["coverage_status"] == "READY_FULL_CANONICAL_COVERAGE"
    assert payload["sections"]["coverage_readiness"]["decision_support_status"] == "READY_FULL_DECISION_SUPPORT"

    mod = _load_ui()
    st = FakeStreamlit()
    mod.render_financial_intelligence_dashboard(
        st,
        project_root=ROOT,
        default_symbol="TUPRS",
    )

    metric_labels = [c[1] for c in st.calls if c and c[0] == "metric"]
    assert "Financial Health" in metric_labels
    assert "Business Quality" in metric_labels
    assert "Base" in metric_labels
    assert "Panel Durumu" in metric_labels
    assert not [c for c in st.calls if c and c[0] == "error"]


def test_active_dashboard_contains_financial_intelligence_route_and_menu_patch():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    assert "FIN_PROD_V7_FINANCIAL_INTELLIGENCE_UI_WIRING_V1" in source
    assert 'elif analiz_modu == "Finansal Zekâ Paneli":' in source
    assert "render_financial_intelligence_dashboard(" in source
    assert '_fin_prod_v7_moduller.index("Temel Analiz") + 1' in source
