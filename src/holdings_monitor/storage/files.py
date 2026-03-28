from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from holdings_monitor.domain.models import DiffReport, HoldingRecord, ValidationReport


class ArtifactStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir

    def prepare_run_dir(self, profile_slug: str, run_id: str) -> Path:
        path = self.root_dir / profile_slug / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_raw_excel(self, run_dir: Path, raw_bytes: bytes) -> Path:
        path = run_dir / "raw.xlsx"
        path.write_bytes(raw_bytes)
        return path

    def write_parsed_csv(self, run_dir: Path, holdings: list[HoldingRecord]) -> Path:
        path = run_dir / "parsed.csv"
        frame = pd.DataFrame([item.to_dict() for item in holdings])
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        return path

    def write_validation_report(self, run_dir: Path, report: ValidationReport) -> Path:
        path = run_dir / "validation.json"
        path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return path

    def write_diff_report(self, run_dir: Path, diff: DiffReport) -> Path:
        path = run_dir / "diff.json"
        path.write_text(json.dumps(diff.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path
