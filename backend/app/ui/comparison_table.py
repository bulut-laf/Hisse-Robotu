from __future__ import annotations

from dataclasses import dataclass
from html import escape


@dataclass(frozen=True, slots=True)
class ComparisonDisplayRow:
    """Arayüzde gösterilecek tek bir karşılaştırma ölçütü."""

    label: str
    base_value: str
    comparison_value: str
    difference: str
    leader: str

    def __post_init__(self) -> None:
        for field_name in (
            "label",
            "base_value",
            "comparison_value",
            "difference",
            "leader",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} metin olmalıdır.")
            if not value.strip():
                raise ValueError(f"{field_name} boş olamaz.")


def compact_comparison_records(
    rows: tuple[ComparisonDisplayRow, ...],
) -> list[dict[str, str]]:
    """Dar ekran tablosu için yalnızca dört temel sütunu döndürür.

    Lider bilgisi yatay tabloyu genişletmemesi için ayrı bir bölümde
    gösterilir. Bu düzen tarayıcı, dar pencere ve yazdırma/PDF görünümünde
    sağ sütunun kesilmesini önler.
    """

    return [
        {
            "Ölçüt": row.label,
            "Baz": row.base_value,
            "Karşılaştırma": row.comparison_value,
            "Fark": row.difference,
        }
        for row in rows
    ]


def comparison_leader_records(
    rows: tuple[ComparisonDisplayRow, ...],
) -> list[dict[str, str]]:
    """Ölçüt liderlerini iki sütunlu, ayrı ve kompakt kayıtlar hâline getirir."""

    return [
        {
            "Ölçüt": row.label,
            "Lider": row.leader,
        }
        for row in rows
        if row.leader != "—"
    ]


def comparison_table_html(
    rows: tuple[ComparisonDisplayRow, ...],
) -> str:
    """Dört sütunu yatay kaydırma olmadan gösteren statik HTML tablo üretir.

    Streamlit ``st.dataframe`` bileşeni tarayıcı yazdırma/PDF görünümünde sağdaki
    sütunları görünür alanın dışında bırakabildiği için karşılaştırma tablosu
    statik ve sabit yerleşimli HTML olarak üretilir. Tüm metinler HTML kaçışından
    geçirilir.
    """

    if not rows:
        return ""

    header = (
        "<thead><tr>"
        "<th>Ölçüt</th><th>Baz</th><th>Karşılaştırma</th><th>Fark</th>"
        "</tr></thead>"
    )
    body_rows = []
    for row in rows:
        body_rows.append(
            "<tr>"
            f"<td>{escape(row.label)}</td>"
            f"<td>{escape(row.base_value)}</td>"
            f"<td>{escape(row.comparison_value)}</td>"
            f"<td>{escape(row.difference)}</td>"
            "</tr>"
        )

    style = """
<style>
.hisse-karsilastirma-wrap {
  width: 100%;
  overflow: visible;
  margin: 0.25rem 0 0.75rem 0;
}
.hisse-karsilastirma {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 0.90rem;
}
.hisse-karsilastirma th,
.hisse-karsilastirma td {
  border: 1px solid rgba(49, 51, 63, 0.16);
  padding: 0.48rem 0.55rem;
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
  word-break: normal;
}
.hisse-karsilastirma th {
  background: rgba(240, 242, 246, 0.92);
  font-weight: 600;
}
.hisse-karsilastirma th:nth-child(1),
.hisse-karsilastirma td:nth-child(1) { width: 36%; }
.hisse-karsilastirma th:nth-child(2),
.hisse-karsilastirma td:nth-child(2) { width: 18%; }
.hisse-karsilastirma th:nth-child(3),
.hisse-karsilastirma td:nth-child(3) { width: 24%; }
.hisse-karsilastirma th:nth-child(4),
.hisse-karsilastirma td:nth-child(4) { width: 22%; }
@media (max-width: 700px) {
  .hisse-karsilastirma { font-size: 0.78rem; }
  .hisse-karsilastirma th,
  .hisse-karsilastirma td { padding: 0.38rem 0.34rem; }
}
@media print {
  .hisse-karsilastirma-wrap { overflow: visible !important; }
  .hisse-karsilastirma { font-size: 9pt; page-break-inside: avoid; }
}
</style>
"""
    return (
        style
        + '<div class="hisse-karsilastirma-wrap">'
        + '<table class="hisse-karsilastirma">'
        + header
        + "<tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
    )
