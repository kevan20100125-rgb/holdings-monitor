from __future__ import annotations

from holdings_monitor.config import ProfileConfig
from holdings_monitor.domain.models import HoldingRecord, ValidationCheck, ValidationReport


class SnapshotValidator:
    def __init__(self, profile: ProfileConfig) -> None:
        self.profile = profile

    def validate(self, holdings: list[HoldingRecord]) -> ValidationReport:
        record_count = len(holdings)
        weight_sum = sum(item.weight_pct for item in holdings)
        missing_values = sum(1 for item in holdings if item.holding_value is None)
        missing_ratio = missing_values / record_count if record_count else 1.0
        symbols = [item.symbol for item in holdings]
        duplicates = sorted({symbol for symbol in symbols if symbols.count(symbol) > 1})
        max_weight_pct = max((item.weight_pct for item in holdings), default=0.0)

        checks = [
            ValidationCheck(
                name="record_count_min",
                passed=record_count >= self.profile.validation.min_records,
                detail=f"record_count={record_count}, min={self.profile.validation.min_records}",
            ),
            ValidationCheck(
                name="record_count_max",
                passed=record_count <= self.profile.validation.max_records,
                detail=f"record_count={record_count}, max={self.profile.validation.max_records}",
            ),
            ValidationCheck(
                name="weight_sum_min",
                passed=weight_sum >= self.profile.validation.weight_sum_min,
                detail=(
                    f"weight_sum={weight_sum:.2f}, min={self.profile.validation.weight_sum_min:.2f}"
                ),
            ),
            ValidationCheck(
                name="weight_sum_max",
                passed=weight_sum <= self.profile.validation.weight_sum_max,
                detail=(
                    f"weight_sum={weight_sum:.2f}, max={self.profile.validation.weight_sum_max:.2f}"
                ),
            ),
            ValidationCheck(
                name="missing_holding_value_ratio",
                passed=missing_ratio <= self.profile.validation.max_missing_holding_value_ratio,
                detail=(
                    f"missing_ratio={missing_ratio:.4f}, "
                    f"max={self.profile.validation.max_missing_holding_value_ratio:.4f}"
                ),
            ),
            ValidationCheck(
                name="duplicate_symbols",
                passed=len(duplicates) == 0,
                detail=f"duplicates={duplicates}",
            ),
            ValidationCheck(
                name="max_single_weight_pct",
                passed=max_weight_pct <= self.profile.validation.max_single_weight_pct,
                detail=(
                    f"max_weight_pct={max_weight_pct:.2f}, "
                    f"max={self.profile.validation.max_single_weight_pct:.2f}"
                ),
            ),
        ]

        passed = all(item.passed for item in checks)
        return ValidationReport(
            passed=passed,
            record_count=record_count,
            weight_sum=weight_sum,
            missing_holding_value_ratio=missing_ratio,
            duplicate_symbols=duplicates,
            max_weight_pct=max_weight_pct,
            checks=checks,
        )
