from backend.app.funds import f5_allocation_read_model


class _FakeSnapshotStore:
    def __init__(self, records):
        self._records = tuple(records)

    def list_records(self):
        return self._records


def test_allocation_known_from_actual_dict_store_schema(monkeypatch):
    fake = _FakeSnapshotStore((
        {
            "canonical_fund_id": "fund:tefas:PHE",
            "data_quality_state": "VALID",
            "positions": [
                {
                    "canonical_fund_id": "fund:tefas:PHE",
                    "symbol": "AKSEN",
                }
            ],
        },
    ))
    monkeypatch.setattr(
        f5_allocation_read_model,
        "fund_portfolio_snapshot_store",
        lambda: fake,
    )
    result = f5_allocation_read_model.allocation_known_by_fund()
    assert result["fund:tefas:PHE"] is True


def test_allocation_unknown_when_positions_empty(monkeypatch):
    fake = _FakeSnapshotStore((
        {
            "canonical_fund_id": "fund:tefas:370001",
            "data_quality_state": "VALID",
            "positions": [],
        },
    ))
    monkeypatch.setattr(
        f5_allocation_read_model,
        "fund_portfolio_snapshot_store",
        lambda: fake,
    )
    result = f5_allocation_read_model.allocation_known_by_fund()
    assert result["fund:tefas:370001"] is False
