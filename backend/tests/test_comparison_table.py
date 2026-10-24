from __future__ import annotations

import pytest

from backend.app.ui.comparison_table import (
    ComparisonDisplayRow,
    compact_comparison_records,
    comparison_leader_records,
    comparison_table_html,
)


def row(
    *,
    label: str = "Toplam getiri",
    base: str = "%425.63",
    comparison: str = "%205.15",
    difference: str = "-220.48 puan",
    leader: str = "Baz ayar",
) -> ComparisonDisplayRow:
    return ComparisonDisplayRow(
        label=label,
        base_value=base,
        comparison_value=comparison,
        difference=difference,
        leader=leader,
    )


def test_compact_records_use_four_columns_only() -> None:
    records = compact_comparison_records((row(),))

    assert tuple(records[0]) == (
        "Ölçüt",
        "Baz",
        "Karşılaştırma",
        "Fark",
    )
    assert "Lider" not in records[0]


def test_compact_records_preserve_values() -> None:
    records = compact_comparison_records((row(),))

    assert records == [
        {
            "Ölçüt": "Toplam getiri",
            "Baz": "%425.63",
            "Karşılaştırma": "%205.15",
            "Fark": "-220.48 puan",
        }
    ]


def test_leaders_are_separated_into_two_columns() -> None:
    records = comparison_leader_records((row(),))

    assert records == [{"Ölçüt": "Toplam getiri", "Lider": "Baz ayar"}]


def test_neutral_leader_is_not_rendered() -> None:
    records = comparison_leader_records((row(leader="—"),))

    assert records == []


def test_record_order_is_preserved() -> None:
    rows = (
        row(label="Toplam getiri"),
        row(label="Maksimum düşüş", leader="Karşılaştırma ayarı"),
    )

    records = compact_comparison_records(rows)

    assert [record["Ölçüt"] for record in records] == [
        "Toplam getiri",
        "Maksimum düşüş",
    ]


def test_empty_text_is_rejected() -> None:
    with pytest.raises(ValueError, match="label boş olamaz"):
        row(label="   ")


def test_html_table_contains_all_four_columns() -> None:
    html = comparison_table_html((row(),))

    assert "<th>Ölçüt</th>" in html
    assert "<th>Baz</th>" in html
    assert "<th>Karşılaştırma</th>" in html
    assert "<th>Fark</th>" in html
    assert "-220.48 puan" in html


def test_html_table_escapes_user_visible_text() -> None:
    html = comparison_table_html(
        (row(label="A < B", difference="+1 & güvenli"),)
    )

    assert "A &lt; B" in html
    assert "+1 &amp; güvenli" in html
    assert "A < B" not in html


def test_html_table_uses_fixed_print_safe_layout() -> None:
    html = comparison_table_html((row(),))

    assert "table-layout: fixed" in html
    assert "@media print" in html
    assert "overflow: visible" in html


def test_html_table_is_empty_when_no_rows_exist() -> None:
    assert comparison_table_html(()) == ""
