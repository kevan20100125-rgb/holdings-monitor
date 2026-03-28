from __future__ import annotations

from holdings_monitor.config import ProfileConfig
from holdings_monitor.domain.models import DiffReport, HoldingRecord


class MessageBuilder:
    def __init__(self, profile: ProfileConfig) -> None:
        self.profile = profile

    def build_diff_message(self, snapshot_date: str, previous_date: str, diff: DiffReport) -> str:
        threshold = self.profile.diff.weight_change_threshold
        max_items = self.profile.diff.max_items_per_section
        lines = [
            f"📢 {self.profile.slug} 持股變動通知",
            f"資料日期：{snapshot_date}",
            f"比較基準：{previous_date}",
            "",
        ]

        if diff.added:
            lines.append(f"新增持股（{len(diff.added)}）")
            for item in diff.added[:max_items]:
                lines.append(f"- 新增：{item.symbol} {item.name} ({item.weight_pct:.2f}%)")
            if len(diff.added) > max_items:
                lines.append(f"- ... 另有 {len(diff.added) - max_items} 檔")
            lines.append("")

        if diff.removed:
            lines.append(f"刪除持股（{len(diff.removed)}）")
            for item in diff.removed[:max_items]:
                lines.append(f"- 移除：{item.symbol} {item.name}")
            if len(diff.removed) > max_items:
                lines.append(f"- ... 另有 {len(diff.removed) - max_items} 檔")
            lines.append("")

        if diff.changed:
            lines.append(f"權重顯著變動（>= {threshold:.2f}%）（{len(diff.changed)}）")
            for item in diff.changed[:max_items]:
                delta = item.weight_delta or 0.0
                sign = "+" if delta >= 0 else ""
                lines.append(
                    f"- 權重調整：{item.symbol} {item.name} "
                    f"({sign}{delta:.2f}%，{item.old_weight_pct:.2f}% -> "
                    f"{item.new_weight_pct:.2f}%)"
                )
            if len(diff.changed) > max_items:
                lines.append(f"- ... 另有 {len(diff.changed) - max_items} 檔")
            lines.append("")

        return "\n".join(lines).strip()

    def build_first_snapshot_message(
        self, snapshot_date: str, holding_count: int, source_url: str
    ) -> str:
        return (
            f"📢 {self.profile.slug} 初始快照建立\n"
            f"資料日期：{snapshot_date}\n"
            "目前尚無更早歷史快照可比較。\n"
            f"持股筆數：{holding_count}\n"
            f"來源：{source_url}"
        )

    def build_validation_failure_message(self, snapshot_date: str, details: str) -> str:
        return (
            f"⚠️ {self.profile.slug} 快照驗證失敗\n"
            f"資料日期：{snapshot_date}\n"
            "本次抓取未升級為正式快照。\n"
            f"原因：{details}"
        )


def format_top_holdings(profile_slug: str, holdings: list[HoldingRecord], top_n: int) -> str:
    lines = ["=" * 72, f"{profile_slug} 前 {min(top_n, len(holdings))} 大持股", "=" * 72]
    for index, item in enumerate(holdings[:top_n], start=1):
        value_text = "-" if item.holding_value is None else f"{int(item.holding_value):,}"
        lines.append(
            f"{index:>2}. {item.symbol} {item.name:<12} 權重 {item.weight_pct:.2f}% "
            f"  金額 {value_text}"
        )
    lines.append("=" * 72)
    return "\n".join(lines)
