from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from holdings_monitor.config import ProfileConfig, RuntimeSettings
from holdings_monitor.domain.models import SnapshotMeta
from holdings_monitor.pipeline.differ import SnapshotDiffer
from holdings_monitor.pipeline.summary import MessageBuilder
from holdings_monitor.pipeline.validator import SnapshotValidator
from holdings_monitor.sources.parsing import PARSER_VERSION, holdings_hash
from holdings_monitor.sources.upamc_excel import UpamcExcelSource
from holdings_monitor.storage.files import ArtifactStore
from holdings_monitor.storage.sqlite import SQLiteRepository
from holdings_monitor.time_utils import now_in_timezone


@dataclass(frozen=True)
class RunResult:
    status: str
    message: str
    snapshot_date: str


class MonitorRunner:
    def __init__(self, profile: ProfileConfig, settings: RuntimeSettings) -> None:
        self.profile = profile
        self.settings = settings
        self.source = UpamcExcelSource(profile)
        self.validator = SnapshotValidator(profile)
        self.differ = SnapshotDiffer()
        self.messages = MessageBuilder(profile)
        self.repo = SQLiteRepository(settings.db_path)
        self.artifacts = ArtifactStore(settings.artifacts_dir)

    def _now(self) -> datetime:
        return now_in_timezone(self.settings.timezone)

    def _run_id(self, snapshot_date: str) -> str:
        return f"{snapshot_date}_{self._now().strftime('%H%M%S')}"

    def run(self, dry_run: bool = False, force_notify: bool = False) -> tuple[RunResult, dict]:
        fetch = self.source.fetch()
        snapshot_date, holdings = self.source.parse(fetch.raw_bytes)
        run_id = self._run_id(snapshot_date)
        run_dir = self.artifacts.prepare_run_dir(self.profile.slug, run_id)
        raw_path = self.artifacts.write_raw_excel(run_dir, fetch.raw_bytes)
        self.artifacts.write_parsed_csv(run_dir, holdings)

        report = self.validator.validate(holdings)
        self.artifacts.write_validation_report(run_dir, report)

        snapshot_hash = holdings_hash(holdings)
        fetched_at = self._now().isoformat(timespec="seconds")
        validation_status = "passed" if report.passed else "failed"
        snapshot_meta = SnapshotMeta(
            profile_slug=self.profile.slug,
            snapshot_date=snapshot_date,
            fetched_at=fetched_at,
            source_url=fetch.source_url,
            holdings_hash=snapshot_hash,
            parser_version=PARSER_VERSION,
            validation_status=validation_status,
            raw_artifact_path=str(raw_path),
        )
        snapshot_id = self.repo.upsert_snapshot(snapshot_meta, holdings)

        existing_previous = self.repo.get_previous_valid_snapshot(self.profile.slug, snapshot_date)
        previous_holdings = []
        previous_snapshot_id = None
        previous_snapshot_date = None
        if existing_previous:
            previous_snapshot_id = int(existing_previous["id"])
            previous_snapshot_date = str(existing_previous["snapshot_date"])
            previous_holdings = self.repo.get_holdings_for_snapshot(previous_snapshot_id)

        diff_report = self.differ.compare(
            previous_holdings, holdings, self.profile.diff.weight_change_threshold
        )
        self.artifacts.write_diff_report(run_dir, diff_report)

        if not report.passed:
            details = "; ".join(
                f"{item.name}={item.detail}" for item in report.checks if not item.passed
            )
            return (
                RunResult(
                    status="validation_failed",
                    message=self.messages.build_validation_failure_message(snapshot_date, details),
                    snapshot_date=snapshot_date,
                ),
                {
                    "snapshot_id": snapshot_id,
                    "compare_snapshot_id": previous_snapshot_id,
                    "diff_report": diff_report,
                    "notify": force_notify,
                    "dry_run": dry_run,
                },
            )

        if previous_snapshot_date is None:
            return (
                RunResult(
                    status="initial_snapshot",
                    message=self.messages.build_first_snapshot_message(
                        snapshot_date,
                        len(holdings),
                        fetch.source_url,
                    ),
                    snapshot_date=snapshot_date,
                ),
                {
                    "snapshot_id": snapshot_id,
                    "compare_snapshot_id": None,
                    "diff_report": diff_report,
                    "notify": force_notify,
                    "dry_run": dry_run,
                },
            )

        if not diff_report.has_changes() and not force_notify:
            message = (
                f"{self.profile.slug} {snapshot_date}: "
                f"no qualifying changes compared with {previous_snapshot_date}"
            )
            return (
                RunResult(
                    status="no_change",
                    message=message,
                    snapshot_date=snapshot_date,
                ),
                {
                    "snapshot_id": snapshot_id,
                    "compare_snapshot_id": previous_snapshot_id,
                    "diff_report": diff_report,
                    "notify": False,
                    "dry_run": dry_run,
                },
            )

        if diff_report.has_changes():
            message = self.messages.build_diff_message(
                snapshot_date,
                previous_snapshot_date,
                diff_report,
            )
            status = "changed"
        else:
            message = (
                f"📢 {self.profile.slug} 強制測試通知\n"
                f"資料日期：{snapshot_date}\n"
                f"比較基準：{previous_snapshot_date}\n"
                "目前無符合門檻的新增、刪除或權重顯著變動，此訊息由 force-notify 送出。"
            )
            status = "forced_notification"

        return (
            RunResult(status=status, message=message, snapshot_date=snapshot_date),
            {
                "snapshot_id": snapshot_id,
                "compare_snapshot_id": previous_snapshot_id,
                "diff_report": diff_report,
                "notify": True,
                "dry_run": dry_run,
            },
        )

    def message_hash(self, message_text: str) -> str:
        return hashlib.sha256(message_text.encode("utf-8")).hexdigest()
