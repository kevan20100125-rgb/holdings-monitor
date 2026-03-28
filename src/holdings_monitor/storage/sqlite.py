from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from holdings_monitor.domain.models import HoldingRecord, SnapshotMeta
from holdings_monitor.exceptions import StorageError


class SQLiteRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise StorageError(str(exc)) from exc
        finally:
            conn.close()

    def init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_slug TEXT NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    holdings_hash TEXT NOT NULL,
                    parser_version TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    raw_artifact_path TEXT NOT NULL,
                    UNIQUE(profile_slug, snapshot_date)
                );

                CREATE TABLE IF NOT EXISTS holdings (
                    snapshot_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    name TEXT NOT NULL,
                    weight_pct REAL NOT NULL,
                    holding_value REAL,
                    shares REAL,
                    currency TEXT NOT NULL,
                    row_hash TEXT NOT NULL,
                    PRIMARY KEY (snapshot_id, symbol),
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS notification_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_slug TEXT NOT NULL,
                    snapshot_id INTEGER NOT NULL,
                    compare_snapshot_id INTEGER,
                    channel TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message_hash TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    sent_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE,
                    FOREIGN KEY (compare_snapshot_id) REFERENCES snapshots(id) ON DELETE SET NULL,
                    UNIQUE(profile_slug, snapshot_id, channel, event_type, message_hash)
                );
                """
            )
            conn.commit()

    def get_snapshot_by_date(self, profile_slug: str, snapshot_date: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM snapshots WHERE profile_slug = ? AND snapshot_date = ?",
                (profile_slug, snapshot_date),
            ).fetchone()
        return row

    def get_previous_valid_snapshot(
        self, profile_slug: str, snapshot_date: str
    ) -> sqlite3.Row | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM snapshots
                WHERE profile_slug = ?
                  AND snapshot_date < ?
                  AND validation_status = 'passed'
                ORDER BY snapshot_date DESC
                LIMIT 1
                """,
                (profile_slug, snapshot_date),
            ).fetchone()
        return row

    def get_holdings_for_snapshot(self, snapshot_id: int) -> list[HoldingRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT symbol, name, weight_pct, holding_value, shares, currency
                FROM holdings
                WHERE snapshot_id = ?
                ORDER BY weight_pct DESC, symbol ASC
                """,
                (snapshot_id,),
            ).fetchall()
        return [
            HoldingRecord(
                symbol=row["symbol"],
                name=row["name"],
                weight_pct=float(row["weight_pct"]),
                holding_value=row["holding_value"],
                shares=row["shares"],
                currency=row["currency"],
            )
            for row in rows
        ]

    def upsert_snapshot(self, snapshot: SnapshotMeta, holdings: list[HoldingRecord]) -> int:
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM snapshots WHERE profile_slug = ? AND snapshot_date = ?",
                (snapshot.profile_slug, snapshot.snapshot_date),
            ).fetchone()

            if existing:
                snapshot_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE snapshots
                    SET fetched_at = ?,
                        source_url = ?,
                        holdings_hash = ?,
                        parser_version = ?,
                        validation_status = ?,
                        raw_artifact_path = ?
                    WHERE id = ?
                    """,
                    (
                        snapshot.fetched_at,
                        snapshot.source_url,
                        snapshot.holdings_hash,
                        snapshot.parser_version,
                        snapshot.validation_status,
                        snapshot.raw_artifact_path,
                        snapshot_id,
                    ),
                )
                conn.execute("DELETE FROM holdings WHERE snapshot_id = ?", (snapshot_id,))
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO snapshots (
                        profile_slug, snapshot_date, fetched_at, source_url,
                        holdings_hash, parser_version, validation_status, raw_artifact_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.profile_slug,
                        snapshot.snapshot_date,
                        snapshot.fetched_at,
                        snapshot.source_url,
                        snapshot.holdings_hash,
                        snapshot.parser_version,
                        snapshot.validation_status,
                        snapshot.raw_artifact_path,
                    ),
                )
                snapshot_id = int(cursor.lastrowid)

            rows = [
                (
                    snapshot_id,
                    item.symbol,
                    item.name,
                    item.weight_pct,
                    item.holding_value,
                    item.shares,
                    item.currency,
                    f"{item.symbol}|{item.name}|{item.weight_pct}|{item.holding_value}|{item.shares}|{item.currency}",
                )
                for item in holdings
            ]
            conn.executemany(
                """
                INSERT INTO holdings (
                    snapshot_id, symbol, name, weight_pct,
                    holding_value, shares, currency, row_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return snapshot_id

    def create_or_get_notification_event(
        self,
        profile_slug: str,
        snapshot_id: int,
        compare_snapshot_id: int | None,
        channel: str,
        event_type: str,
        message_hash: str,
        message_text: str,
        created_at: str,
    ) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, status, retry_count
                FROM notification_events
                WHERE profile_slug = ?
                  AND snapshot_id = ?
                  AND channel = ?
                  AND event_type = ?
                  AND message_hash = ?
                """,
                (profile_slug, snapshot_id, channel, event_type, message_hash),
            ).fetchone()
            if row:
                return dict(row)

            cursor = conn.execute(
                """
                INSERT INTO notification_events (
                    profile_slug, snapshot_id, compare_snapshot_id, channel,
                    event_type, message_hash, message_text, status,
                    retry_count, last_error, sent_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, NULL, NULL, ?, ?)
                """,
                (
                    profile_slug,
                    snapshot_id,
                    compare_snapshot_id,
                    channel,
                    event_type,
                    message_hash,
                    message_text,
                    created_at,
                    created_at,
                ),
            )
        return {"id": int(cursor.lastrowid), "status": "pending", "retry_count": 0}

    def mark_notification_sent(self, event_id: int, sent_at: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE notification_events
                SET status = 'sent', sent_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (sent_at, sent_at, event_id),
            )

    def mark_notification_failed(self, event_id: int, error: str, updated_at: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE notification_events
                SET status = 'failed', retry_count = retry_count + 1, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (error, updated_at, event_id),
            )

    def list_pending_or_failed_notifications(self, profile_slug: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, channel, message_text, retry_count, status
                FROM notification_events
                WHERE profile_slug = ? AND status IN ('pending', 'failed')
                ORDER BY id ASC
                """,
                (profile_slug,),
            ).fetchall()
        return [dict(row) for row in rows]
