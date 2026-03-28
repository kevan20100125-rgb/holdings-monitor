from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from holdings_monitor.config import load_profile, load_runtime_settings, resolve_profile_path
from holdings_monitor.env import load_environment
from holdings_monitor.logging_utils import configure_logging
from holdings_monitor.notify.line import LineNotifier
from holdings_monitor.notify.stdout import StdoutNotifier
from holdings_monitor.pipeline.run_monitor import MonitorRunner
from holdings_monitor.pipeline.summary import format_top_holdings
from holdings_monitor.storage.sqlite import SQLiteRepository

LOGGER = logging.getLogger(__name__)


def project_root() -> Path:
    env_root = os.getenv("HOLDINGS_MONITOR_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Public-ready holdings monitor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="fetch, validate, persist, diff, and optionally notify")
    run.add_argument(
        "--profile",
        required=False,
        help="path to profile yaml; defaults to HOLDINGS_MONITOR_PROFILE when set",
    )
    run.add_argument("--dry-run", action="store_true", help="do not send notifications")
    run.add_argument("--force-notify", action="store_true", help="send even when there is no diff")
    run.add_argument("--print-top", type=int, default=0, help="print top N holdings after fetch")

    verify = subparsers.add_parser("verify-line", help="verify LINE credentials")
    verify.add_argument("--json", action="store_true", help="print raw profile json")

    test = subparsers.add_parser("test-line", help="send a LINE test message")
    test.add_argument("--message", default="", help="custom test message")

    retry = subparsers.add_parser(
        "retry-notifications", help="retry pending or failed notifications"
    )
    retry.add_argument(
        "--profile",
        required=False,
        help="path to profile yaml; defaults to HOLDINGS_MONITOR_PROFILE when set",
    )

    return parser


def build_notifiers(channel_names: list[str], settings) -> dict[str, object]:
    notifiers: dict[str, object] = {}
    for name in channel_names:
        if name == "stdout":
            notifiers[name] = StdoutNotifier()
        elif name == "line":
            notifiers[name] = LineNotifier(settings)
        else:
            raise ValueError(f"unsupported notifier channel: {name}")
    return notifiers


def cmd_verify_line(args: argparse.Namespace) -> int:
    settings = load_runtime_settings(project_root())
    notifier = LineNotifier(settings)
    profile = notifier.verify()
    if args.json:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        print(f"LINE verify OK: {profile.get('displayName', '')} ({profile.get('userId', '')})")
    return 0


def cmd_test_line(args: argparse.Namespace) -> int:
    settings = load_runtime_settings(project_root())
    notifier = LineNotifier(settings)
    text = args.message or "✅ holdings-monitor test message"
    notifier.send(text)
    print("LINE test message sent")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    settings = load_runtime_settings(project_root())
    profile_path = resolve_profile_path(args.profile, settings)
    profile = load_profile(profile_path, settings)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    runner = MonitorRunner(profile, settings)
    result, context = runner.run(dry_run=args.dry_run, force_notify=args.force_notify)
    print(result.message)

    if args.print_top > 0:
        snapshot_row = runner.repo.get_snapshot_by_date(profile.slug, result.snapshot_date)
        if snapshot_row:
            holdings = runner.repo.get_holdings_for_snapshot(int(snapshot_row["id"]))
            print(format_top_holdings(profile.slug, holdings, args.print_top))

    if not context["notify"] or args.dry_run:
        if args.dry_run:
            LOGGER.info("dry-run enabled; notifications skipped")
        return 0

    notifiers = build_notifiers(profile.notifications.channels, settings)
    message_hash = runner.message_hash(result.message)
    timestamp = runner._now().isoformat(timespec="seconds")

    for channel_name, notifier in notifiers.items():
        event = runner.repo.create_or_get_notification_event(
            profile_slug=profile.slug,
            snapshot_id=context["snapshot_id"],
            compare_snapshot_id=context["compare_snapshot_id"],
            channel=channel_name,
            event_type=result.status,
            message_hash=message_hash,
            message_text=result.message,
            created_at=timestamp,
        )
        if event["status"] == "sent":
            LOGGER.info(
                "skip already-sent notification channel=%s event_id=%s",
                channel_name,
                event["id"],
            )
            continue
        try:
            notifier.send(result.message)
            runner.repo.mark_notification_sent(
                event["id"],
                sent_at=runner._now().isoformat(timespec="seconds"),
            )
        except Exception as exc:
            runner.repo.mark_notification_failed(
                event["id"],
                error=str(exc),
                updated_at=runner._now().isoformat(timespec="seconds"),
            )
            LOGGER.exception("notification failed channel=%s error=%s", channel_name, exc)
    return 0


def cmd_retry_notifications(args: argparse.Namespace) -> int:
    settings = load_runtime_settings(project_root())
    profile_path = resolve_profile_path(args.profile, settings)
    profile = load_profile(profile_path, settings)
    repo = SQLiteRepository(settings.db_path)
    notifiers = build_notifiers(profile.notifications.channels, settings)
    pending = repo.list_pending_or_failed_notifications(profile.slug)
    if not pending:
        print("No pending or failed notifications.")
        return 0

    for item in pending:
        channel = item["channel"]
        notifier = notifiers.get(channel)
        if notifier is None:
            LOGGER.warning("skip unknown notifier channel=%s", channel)
            continue
        now_text = datetime.utcnow().isoformat(timespec="seconds")
        try:
            notifier.send(item["message_text"])
            repo.mark_notification_sent(item["id"], sent_at=now_text)
            print(f"Retried notification {item['id']} via {channel}: sent")
        except Exception as exc:
            repo.mark_notification_failed(item["id"], error=str(exc), updated_at=now_text)
            print(f"Retried notification {item['id']} via {channel}: failed -> {exc}")
    return 0


def main() -> int:
    root = project_root()
    load_environment(root)
    settings = load_runtime_settings(root)
    configure_logging(settings.log_dir, settings.log_level)

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "verify-line":
        return cmd_verify_line(args)
    if args.command == "test-line":
        return cmd_test_line(args)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "retry-notifications":
        return cmd_retry_notifications(args)
    raise RuntimeError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
