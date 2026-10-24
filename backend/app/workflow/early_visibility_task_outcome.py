from dataclasses import dataclass

@dataclass(frozen=True)
class EarlyVisibilityTaskOutcome:
    symbol: str
    outcome: str
    task_type: str
    source: str = "EARLY_VISIBILITY"

def record_early_visibility_task_outcome(symbol: str, outcome: str = "RECORDED"):
    return EarlyVisibilityTaskOutcome(
        symbol=str(symbol).upper(),
        outcome=str(outcome).upper(),
        task_type="RESEARCH_REVIEW",
    )
