from pathlib import Path


def test_v1_operations_01c_dashboard_wires_morning_candidate_flow():
    dashboard = Path("backend/dashboard.py").read_text(encoding="utf-8")

    assert "build_morning_operation_snapshot" in dashboard
    assert "morning_candidate_rows" in dashboard
    assert "build_current_visibility_context" in dashboard
    assert 'st.session_state.get("bist_toplu_tarama_son_sonuc")' in dashboard
    assert 'st.markdown("#### Bugünün 5 Adayı")' in dashboard
    assert "limit=5" in dashboard
    assert "V1_OPERATIONS_01C_MORNING_CANDIDATE_UI" in dashboard


def test_v1_operations_01c_preserves_existing_authorities():
    dashboard = Path("backend/dashboard.py").read_text(encoding="utf-8")
    marker = dashboard.index("V1_OPERATIONS_01C_MORNING_CANDIDATE_UI")
    end = dashboard.index("V11_TRACK1_OBSERVABILITY_UI", marker)
    block = dashboard[marker:end]

    assert "build_morning_operation_snapshot" in block
    assert "morning_candidate_rows" in block
    assert "manuel tarama zorunlu değildir" in block
    assert "build_daily_buy_decisions" in block
    assert "BIST 100 otomatik taranıyor" in block
