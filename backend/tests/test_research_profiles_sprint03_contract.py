
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_same_ranking_memory_file_is_reused():
    memory = read("backend/app/analysis/ranking_memory.py")
    helper = read("backend/app/analysis/research_profile_memory.py")
    assert "rank_observations.jsonl" in memory
    assert "profile_observations.jsonl" not in memory
    assert "profile_observations.jsonl" not in helper
    assert "append_profile_snapshot" in memory


def test_rank_reader_ignores_profile_record_family():
    memory = read("backend/app/analysis/ranking_memory.py")
    assert 'payload.get("record_type", "rank") != "rank"' in memory
    assert 'PROFILE_RECORD_TYPE = "research_profile"' in memory


def test_forward_only_activation_and_no_replay():
    helper = read("backend/app/analysis/research_profile_memory.py")
    assert "date(2026, 8, 26)" in helper
    assert "WARMING_UP" in helper
    assert "backfill" in helper.lower()
    assert "historical_replay" not in helper


def test_dashboard_persists_profile_bundle_without_trade_authority():
    dashboard = read("backend/dashboard.py")
    assert "RPV1_SPRINT03_PROFILE_MEMORY_WRITE" in dashboard
    assert "persist_research_profile_bundle(" in dashboard
    assert "universe_name=sonuc.evren_adi" in dashboard


def test_ui_contains_profile_lifecycle_and_existing_rank_context():
    ui = read("backend/app/ui/research_profiles_dashboard.py")
    assert "MATCH serisi" in ui
    assert "Profil olayı" in ui
    assert "Sıra yolu" in ui
    assert "Early Visibility" in ui
    assert 'item["Skor"]' not in ui


def test_no_new_scoring_or_al_sat_authority():
    joined = (
        read("backend/app/analysis/research_profile_memory.py")
        + read("backend/app/ui/research_profiles_dashboard.py")
    ).lower()
    assert "calculate_score" not in joined
    assert "position_size" not in joined
    assert "al_sat" not in joined
