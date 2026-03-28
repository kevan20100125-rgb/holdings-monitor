from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_environment(project_root: Path | None = None) -> None:
    explicit_env = os.getenv("HOLDINGS_MONITOR_ENV_FILE", "").strip()
    if explicit_env:
        load_dotenv(dotenv_path=Path(explicit_env).expanduser(), override=False)
        return

    if project_root is None:
        load_dotenv(override=False)
        return

    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path, override=False)
