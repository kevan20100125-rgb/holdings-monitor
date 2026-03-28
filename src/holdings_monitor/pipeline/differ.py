from __future__ import annotations

from holdings_monitor.domain.models import DiffEntry, DiffReport, HoldingRecord


class SnapshotDiffer:
    def compare(
        self,
        previous: list[HoldingRecord],
        current: list[HoldingRecord],
        threshold: float,
    ) -> DiffReport:
        prev_map = {item.symbol: item for item in previous}
        curr_map = {item.symbol: item for item in current}

        added = [
            DiffEntry(symbol=item.symbol, name=item.name, weight_pct=item.weight_pct)
            for item in current
            if item.symbol not in prev_map
        ]
        removed = [
            DiffEntry(symbol=item.symbol, name=item.name, weight_pct=item.weight_pct)
            for item in previous
            if item.symbol not in curr_map
        ]

        changed: list[DiffEntry] = []
        for symbol in sorted(set(prev_map).intersection(curr_map)):
            old = prev_map[symbol]
            new = curr_map[symbol]
            delta = new.weight_pct - old.weight_pct
            if abs(delta) >= threshold:
                changed.append(
                    DiffEntry(
                        symbol=symbol,
                        name=new.name,
                        old_weight_pct=old.weight_pct,
                        new_weight_pct=new.weight_pct,
                        weight_delta=delta,
                    )
                )

        added.sort(key=lambda item: item.weight_pct or 0.0, reverse=True)
        removed.sort(key=lambda item: item.weight_pct or 0.0, reverse=True)
        changed.sort(key=lambda item: abs(item.weight_delta or 0.0), reverse=True)
        return DiffReport(added=added, removed=removed, changed=changed)
