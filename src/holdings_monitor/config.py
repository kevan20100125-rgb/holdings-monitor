from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SourceConfig:
    type: str
    fund_code: str
    export_url: str


@dataclass(frozen=True)
class ValidationConfig:
    min_records: int
    max_records: int
    weight_sum_min: float
    weight_sum_max: float
    max_missing_holding_value_ratio: float
    max_single_weight_pct: float


@dataclass(frozen=True)
class DiffConfig:
    weight_change_threshold: float
    max_items_per_section: int


@dataclass(frozen=True)
class NotificationConfig:
    channels: list[str]


@dataclass(frozen=True)
class StorageConfig:
    currency: str


@dataclass(frozen=True)
class ProfileConfig:
    name: str
    slug: str
    description: str
    source: SourceConfig
    validation: ValidationConfig
    diff: DiffConfig
    notifications: NotificationConfig
    storage: StorageConfig


@dataclass(frozen=True)
class RuntimeSettings:
    env: str
    project_root: Path
    data_dir: Path
    log_dir: Path
    db_path: Path
    default_profile_path: Path | None
    log_level: str
    timezone: str
    source_export_url_override: str
    line_channel_access_token: str
    line_to_user_id: str

    @property
    def artifacts_dir(self) -> Path:
        return self.data_dir / "artifacts"


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"invalid config file: {path}")
    return data


def _resolve_path(project_root: Path, raw_value: str | Path | None, default: str | Path) -> Path:
    value = Path(raw_value) if raw_value not in (None, "") else Path(default)
    if value.is_absolute():
        return value
    return project_root / value


def load_profile(path: str | Path, settings: RuntimeSettings | None = None) -> ProfileConfig:
    data = _read_yaml(Path(path))
    source_data = dict(data["source"])
    if settings and settings.source_export_url_override:
        source_data["export_url"] = settings.source_export_url_override
    return ProfileConfig(
        name=str(data["name"]),
        slug=str(data.get("slug", data["name"])),
        description=str(data.get("description", "")),
        source=SourceConfig(**source_data),
        validation=ValidationConfig(**data["validation"]),
        diff=DiffConfig(**data["diff"]),
        notifications=NotificationConfig(**data["notifications"]),
        storage=StorageConfig(**data["storage"]),
    )


def load_runtime_settings(project_root: Path | None = None) -> RuntimeSettings:
    base_root = Path(
        os.getenv("HOLDINGS_MONITOR_PROJECT_ROOT", project_root or Path.cwd())
    ).expanduser()
    base_root = base_root.resolve()

    data_dir = _resolve_path(
        base_root,
        os.getenv("HOLDINGS_MONITOR_DATA_DIR"),
        "data",
    )
    log_dir = _resolve_path(
        base_root,
        os.getenv("HOLDINGS_MONITOR_LOG_DIR"),
        "logs",
    )
    db_path = _resolve_path(
        base_root,
        os.getenv("HOLDINGS_MONITOR_DB_PATH"),
        data_dir / "holdings_monitor.db",
    )
    raw_profile = os.getenv("HOLDINGS_MONITOR_PROFILE", "").strip()
    default_profile_path = (
        _resolve_path(base_root, raw_profile, raw_profile) if raw_profile else None
    )

    return RuntimeSettings(
        env=os.getenv("HOLDINGS_MONITOR_ENV", "development"),
        project_root=base_root,
        data_dir=data_dir,
        log_dir=log_dir,
        db_path=db_path,
        default_profile_path=default_profile_path,
        log_level=os.getenv("HOLDINGS_MONITOR_LOG_LEVEL", "INFO"),
        timezone=os.getenv("HOLDINGS_MONITOR_TIMEZONE", "Asia/Taipei").strip() or "Asia/Taipei",
        source_export_url_override=os.getenv(
            "HOLDINGS_MONITOR_SOURCE_EXPORT_URL_OVERRIDE", ""
        ).strip(),
        line_channel_access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip(),
        line_to_user_id=os.getenv("LINE_TO_USER_ID", "").strip(),
    )


def resolve_profile_path(provided_path: str | Path | None, settings: RuntimeSettings) -> Path:
    if provided_path:
        path = Path(provided_path).expanduser()
        return path if path.is_absolute() else (settings.project_root / path)
    if settings.default_profile_path is not None:
        return settings.default_profile_path
    raise ValueError(
        "profile path is required. Pass --profile or set "
        "HOLDINGS_MONITOR_PROFILE in the environment."
    )
