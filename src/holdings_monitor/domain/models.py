from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class HoldingRecord:
    symbol: str
    name: str
    weight_pct: float
    holding_value: float | None
    shares: float | None = None
    currency: str = "TWD"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SnapshotMeta:
    profile_slug: str
    snapshot_date: str
    fetched_at: str
    source_url: str
    holdings_hash: str
    parser_version: str
    validation_status: str
    raw_artifact_path: str


@dataclass(frozen=True)
class ValidationCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ValidationReport:
    passed: bool
    record_count: int
    weight_sum: float
    missing_holding_value_ratio: float
    duplicate_symbols: list[str]
    max_weight_pct: float
    checks: list[ValidationCheck]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "record_count": self.record_count,
            "weight_sum": self.weight_sum,
            "missing_holding_value_ratio": self.missing_holding_value_ratio,
            "duplicate_symbols": self.duplicate_symbols,
            "max_weight_pct": self.max_weight_pct,
            "checks": [asdict(item) for item in self.checks],
        }


@dataclass(frozen=True)
class DiffEntry:
    symbol: str
    name: str
    weight_pct: float | None = None
    old_weight_pct: float | None = None
    new_weight_pct: float | None = None
    weight_delta: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiffReport:
    added: list[DiffEntry]
    removed: list[DiffEntry]
    changed: list[DiffEntry]

    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added": [item.to_dict() for item in self.added],
            "removed": [item.to_dict() for item in self.removed],
            "changed": [item.to_dict() for item in self.changed],
        }
