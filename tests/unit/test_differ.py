from holdings_monitor.domain.models import HoldingRecord
from holdings_monitor.pipeline.differ import SnapshotDiffer


def test_compare_detects_added_removed_and_changed() -> None:
    previous = [
        HoldingRecord(symbol="2330", name="台積電", weight_pct=10.0, holding_value=100.0),
        HoldingRecord(symbol="2454", name="聯發科", weight_pct=8.0, holding_value=90.0),
    ]
    current = [
        HoldingRecord(symbol="2330", name="台積電", weight_pct=11.2, holding_value=101.0),
        HoldingRecord(symbol="2382", name="廣達", weight_pct=3.0, holding_value=50.0),
    ]
    diff = SnapshotDiffer().compare(previous, current, threshold=1.0)
    assert [item.symbol for item in diff.added] == ["2382"]
    assert [item.symbol for item in diff.removed] == ["2454"]
    assert [item.symbol for item in diff.changed] == ["2330"]
    assert round(diff.changed[0].weight_delta or 0.0, 2) == 1.2
