from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.app.analysis.bist_universe import (
    BistUniverseError,
    BistUniverseRepository,
)
from backend.app.sector_analysis.sector_member_strength import (
    DEFAULT_MEMBER_SECTORS,
    SectorMemberStrengthError,
    SectorMemberStrengthMap,
    SectorMemberStrengthResult,
    build_sector_member_strength_map,
)


@dataclass(frozen=True, slots=True)
class CandidateSectorContext:
    """Bir tarama adayının birincil sektör bağlamı."""

    symbol: str
    sector_code: str
    sector_name: str
    sector_score: int
    sector_status: str
    sector_confidence: str
    relative_composite: float
    label: str


@dataclass(frozen=True, slots=True)
class CandidateSectorContextBundle:
    """Aday sektör bağlamları ve bağlam üretimindeki sınırlamalar."""

    contexts: dict[str, CandidateSectorContext]
    reference_universe: str
    errors: tuple[str, ...] = ()


# XUSIN / XUHIZ / XUMAL geniş üst gruplardır. Bir hisse aynı zamanda
# daha özgül bir sektör endeksinde yer alıyorsa özgül sektör seçilir.
_BROAD_SECTOR_CODES = frozenset({"XUSIN", "XUHIZ", "XUMAL"})
_SECTOR_ORDER = {
    definition.code: order
    for order, definition in enumerate(DEFAULT_MEMBER_SECTORS)
}


def _normalize_symbol(symbol: str) -> str:
    value = str(symbol).lstrip("\ufeff").strip().upper()
    if value.endswith(".E"):
        value = value.removesuffix(".E")
    if "." not in value:
        value = f"{value}.IS"
    return value


def _sector_specificity(code: str) -> int:
    return 0 if code in _BROAD_SECTOR_CODES else 1


def _context_label(item: SectorMemberStrengthResult) -> str:
    if item.status == "Güçlü":
        return "Güçlü sektör desteği"
    if item.status == "Pozitif":
        return "Pozitif sektör desteği"
    if item.status == "Nötr":
        return "Nötr sektör bağlamı"
    return "Zayıf sektör bağlamı"


def build_candidate_sector_contexts(
    symbols: Iterable[str],
    *,
    strength_map: SectorMemberStrengthMap,
    repository: BistUniverseRepository | None = None,
) -> CandidateSectorContextBundle:
    """
    Adayları mevcut sektör güç haritasıyla eşleştirir.

    Bu fonksiyon adayları elemez, teknik skoru değiştirmez ve yeni bir
    işlem sinyali üretmez. Bir hisse hem geniş hem özgül sektördeyse
    özgül sektör tercih edilir.
    """
    repo = repository or BistUniverseRepository()
    normalized = tuple(
        dict.fromkeys(
            _normalize_symbol(symbol)
            for symbol in symbols
            if str(symbol).strip()
        )
    )

    memberships: dict[str, set[str]] = {}
    errors: list[str] = []

    for item in strength_map.items:
        try:
            universe = repo.endeks_bilesenlerini_yukle(
                item.code,
                endeks_adi=item.name,
                internetten_guncelle=False,
            )
            memberships[item.code] = set(universe.semboller)
        except (BistUniverseError, ValueError, OSError) as exc:
            errors.append(f"{item.code}: {exc}")

    contexts: dict[str, CandidateSectorContext] = {}

    for symbol in normalized:
        matches = [
            item
            for item in strength_map.items
            if symbol in memberships.get(item.code, set())
        ]
        if not matches:
            continue

        selected = min(
            matches,
            key=lambda item: (
                -_sector_specificity(item.code),
                _SECTOR_ORDER.get(item.code, 10_000),
                item.code,
            ),
        )

        contexts[symbol] = CandidateSectorContext(
            symbol=symbol,
            sector_code=selected.code,
            sector_name=selected.name,
            sector_score=selected.strength_score,
            sector_status=selected.status,
            sector_confidence=selected.confidence,
            relative_composite=selected.relative_composite,
            label=_context_label(selected),
        )

    return CandidateSectorContextBundle(
        contexts=contexts,
        reference_universe=strength_map.reference_universe,
        errors=tuple(errors) + tuple(strength_map.errors),
    )


def build_live_candidate_sector_contexts(
    symbols: Iterable[str],
    *,
    reference_universe: str = "BIST 100",
    repository: BistUniverseRepository | None = None,
) -> CandidateSectorContextBundle:
    """
    Canlı sektör güç haritasını oluşturup adaylarla eşleştirir.

    Üyelik verisi aynı repository/cache zincirinden okunur. Sektör analizi
    başarısız olursa çağıran katman teknik taramayı yine de koruyabilir.
    """
    repo = repository or BistUniverseRepository()

    try:
        strength_map = build_sector_member_strength_map(
            reference_universe=reference_universe,
            repository=repo,
            # Ana tarama zaten resmi BIST üyelik kaynağını yenileyebildiği için
            # aynı işlemde ikinci bir internet üyelik çağrısı yapmıyoruz.
            refresh_membership=False,
        )
    except (SectorMemberStrengthError, BistUniverseError, ValueError) as exc:
        raise SectorMemberStrengthError(
            f"Aday sektör bağlamı üretilemedi: {exc}"
        ) from exc

    return build_candidate_sector_contexts(
        symbols,
        strength_map=strength_map,
        repository=repo,
    )
