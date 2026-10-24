from backend.app.workflow.task_engine_v1 import (
    QualityState,
    WorkflowPhase,
    build_tasks,
)


def test_stale_data_blocks_new_analysis_but_not_position_management():
    quality=QualityState(freshness_ok=False)
    tasks=build_tasks(
        phase=WorkflowPhase.IN_SESSION,
        quality=quality,
        shortlist_count=4,
        open_position_count=2,
    )
    by_id={task.task_id:task for task in tasks}
    assert by_id["technical"].blocked is True
    assert by_id["risk"].blocked is True
    assert by_id["positions"].blocked is False


def test_weekly_flow_reuses_existing_modules():
    tasks=build_tasks(
        phase=WorkflowPhase.WEEKLY_REVIEW,
        quality=QualityState(),
    )
    modules={task.target_module for task in tasks}
    assert "Fırsat Radarı" in modules
    assert "Momentum Keşif" in modules
    assert "Ön Yükseliş Hazırlık" in modules
    assert "Ön Yükseliş Toplu Doğrulama" in modules
    assert "Haftalık Performans Raporu" in modules


def test_pre_session_quality_gate():
    tasks=build_tasks(
        phase=WorkflowPhase.PRE_SESSION,
        quality=QualityState(security_lock=True),
        shortlist_count=5,
    )
    by_id={task.task_id:task for task in tasks}
    assert by_id["data_quality"].blocked is False
    assert by_id["regime"].blocked is True
    assert by_id["shortlist"].blocked is True
