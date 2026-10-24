from __future__ import annotations
from dataclasses import dataclass
from typing import Final

SUPPORTED_SECTOR_MODELS: Final[tuple[str, ...]] = (
    "INDUSTRIAL", "BANK", "INSURANCE", "REIT", "HOLDING",
)
PRODUCTION_READY_MODELS: Final[tuple[str, ...]] = ("INDUSTRIAL",)

@dataclass(frozen=True)
class SectorModelRoute:
    requested_model: str
    resolved_model: str | None
    status: str
    production_ready: bool
    blocker: str | None

def normalize_sector_model(value: object) -> str:
    return str(value or "").strip().upper()

def resolve_sector_model_route(sector_model: object) -> SectorModelRoute:
    requested = normalize_sector_model(sector_model)
    if not requested:
        return SectorModelRoute("", None, "BLOCKED", False, "SECTOR_MODEL_MISSING")
    if requested not in SUPPORTED_SECTOR_MODELS:
        return SectorModelRoute(requested, None, "BLOCKED", False, f"SECTOR_MODEL_UNSUPPORTED:{requested}")
    if requested not in PRODUCTION_READY_MODELS:
        return SectorModelRoute(requested, requested, "BLOCKED", False, f"DEDICATED_{requested}_MODEL_REQUIRED")
    return SectorModelRoute(requested, requested, "PASS", True, None)

def assert_sector_model_production_ready(sector_model: object) -> str:
    route = resolve_sector_model_route(sector_model)
    if route.status != "PASS" or not route.production_ready:
        raise ValueError(route.blocker or "SECTOR_MODEL_NOT_PRODUCTION_READY")
    assert route.resolved_model is not None
    return route.resolved_model

__all__ = [
    "SUPPORTED_SECTOR_MODELS", "PRODUCTION_READY_MODELS", "SectorModelRoute",
    "normalize_sector_model", "resolve_sector_model_route",
    "assert_sector_model_production_ready",
]
