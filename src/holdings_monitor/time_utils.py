from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone, tzinfo

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


DEFAULT_TIMEZONE = "Asia/Taipei"


def get_timezone(timezone_name: str | None) -> tzinfo:
    name = (timezone_name or DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    if name == "Asia/Taipei":
        return timezone(timedelta(hours=8))
    return UTC


def now_in_timezone(timezone_name: str | None) -> datetime:
    return datetime.now(get_timezone(timezone_name))
