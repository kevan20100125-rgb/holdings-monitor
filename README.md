# holdings-monitor

A config-driven holdings disclosure monitor for ETF and fund portfolios.

`holdings-monitor` fetches a source file, parses holdings, validates the snapshot, stores history, computes diffs, persists raw artifacts, and sends notifications through pluggable channels.

This repository is designed for **public GitHub use, reusable deployment, and user-specific configuration through environment variables**.

---

## Features

- Config-driven profile system
- Source adapter architecture
- Snapshot history stored in SQLite
- Raw artifact retention for debugging
- Validation gate to prevent bad snapshots from becoming canonical
- Diff reporting between valid snapshots
- Notification retry workflow
- Built-in `stdout` notifier
- Optional LINE Messaging API notifier
- Docker-ready layout
- systemd deployment templates

---

## Repository layout

```text
holdings-monitor/
├─ src/holdings_monitor/
│  ├─ cli.py
│  ├─ config.py
│  ├─ notify/
│  ├─ pipeline/
│  ├─ sources/
│  └─ storage/
├─ configs/
│  └─ profiles/
│     ├─ examples/
│     └─ local/
├─ deploy/
│  └─ systemd/
├─ tests/
├─ Dockerfile
├─ docker-compose.yml
├─ .env.example
└─ README.md
```

---

## Supported execution model

This project is a **stateful batch monitor**.

It is intended to be run:
- manually from the CLI
- through Docker
- from `cron`
- from a `systemd` timer

It is **not** a web server, daemon, or built-in scheduler.

---

## Quick start (Conda)

```bash
conda create -n holdings-monitor python=3.12 -y
conda activate holdings-monitor
python -m pip install -e .[dev]
cp .env.example .env
```

Create a local profile:

```bash
mkdir -p configs/profiles/local
cp configs/profiles/examples/upamc-00981A.yaml configs/profiles/local/my-profile.yaml
```

Set the default profile path in `.env`:

```bash
HOLDINGS_MONITOR_PROFILE=configs/profiles/local/my-profile.yaml
```

Run a dry run:

```bash
holdings-monitor run --dry-run --print-top 10
```

Run with an explicit profile:

```bash
holdings-monitor run --profile configs/profiles/local/my-profile.yaml --dry-run --print-top 10
```

---

## Environment variables

### Core runtime

```bash
HOLDINGS_MONITOR_ENV=development
HOLDINGS_MONITOR_PROFILE=configs/profiles/local/my-profile.yaml
HOLDINGS_MONITOR_DATA_DIR=data
HOLDINGS_MONITOR_LOG_DIR=logs
HOLDINGS_MONITOR_DB_PATH=data/holdings_monitor.db
HOLDINGS_MONITOR_LOG_LEVEL=INFO
HOLDINGS_MONITOR_TIMEZONE=Asia/Taipei
```

### Optional source override

```bash
HOLDINGS_MONITOR_SOURCE_EXPORT_URL_OVERRIDE=
```

Use this when you want to override the source export URL without editing the profile file.

### Optional LINE notifier

```bash
LINE_CHANNEL_ACCESS_TOKEN=
LINE_TO_USER_ID=
```

LINE is optional. The public example profile uses `stdout` only.

### Deployment helper variables

```bash
HOLDINGS_MONITOR_PROJECT_ROOT=
HOLDINGS_MONITOR_PYTHON_BIN=
HOLDINGS_MONITOR_RANDOM_DELAY_MAX_SECONDS=5400
HOLDINGS_MONITOR_LOCK_FILE=/tmp/holdings-monitor.lock
HOLDINGS_MONITOR_RUNNER_LOG_FILE=
PYTHONNOUSERSITE=1
```

---

## CLI commands

### Run the monitor

```bash
holdings-monitor run
```

### Run with explicit profile

```bash
holdings-monitor run --profile configs/profiles/local/my-profile.yaml
```

### Dry run

```bash
holdings-monitor run --dry-run --print-top 10
```

### Force a notification even when there is no diff

```bash
holdings-monitor run --force-notify
```

### Verify LINE credentials

```bash
holdings-monitor verify-line
```

### Send a LINE test message

```bash
holdings-monitor test-line --message "monitor online"
```

### Retry failed or pending notifications

```bash
holdings-monitor retry-notifications
```

---

## Profiles

Profiles live under `configs/profiles/`.

### Public examples
Store reusable sample profiles in:

```text
configs/profiles/examples/
```

### Local/private profiles
Store user-specific profiles in:

```text
configs/profiles/local/
```

`configs/profiles/local/` should be ignored by Git.

### Example profile fields

- source type and URL
- validation thresholds
- diff thresholds
- notification channels
- storage metadata such as currency

---

## Notifications

Supported notifier channels currently include:

- `stdout`
- `line`

For public examples, use:

```yaml
notifications:
  channels:
    - stdout
```

To enable LINE in your local profile:

```yaml
notifications:
  channels:
    - stdout
    - line
```

Then set `LINE_CHANNEL_ACCESS_TOKEN` and `LINE_TO_USER_ID` in your environment.

---

## Artifacts generated per run

Artifacts are written under:

```text
data/artifacts/<profile_slug>/<run_id>/
```

Each run can generate:

- `raw.xlsx`
- `parsed.csv`
- `validation.json`
- `diff.json`

This is useful for debugging source changes and parser failures.

---

## Docker

Build and run:

```bash
docker compose build
docker compose run --rm monitor run --dry-run
```

If your `.env` sets `HOLDINGS_MONITOR_PROFILE`, the default `run` command is enough.

---

## systemd deployment

Example user-level systemd files are included under:

```text
deploy/systemd/
```

See:

```text
deploy/systemd/README.md
```

This setup supports:
- daily execution after 18:00
- randomized delay
- lock protection
- environment-file based deployment
- no hard-coded private paths in tracked files

---

## Example cron entry

```cron
15 18 * * 1-5 cd /path/to/holdings-monitor && /usr/bin/docker compose run --rm monitor run >> logs/cron.log 2>&1
```

For long-term host-based deployment, systemd is recommended over cron.

---

## Development

Install development dependencies:

```bash
python -m pip install -e .[dev]
```

Run checks:

```bash
ruff check .
python -m pytest
```

---

## Security

Do not commit:
- `.env`
- database files
- `data/`
- `logs/`
- generated CSV/XLSX files
- local profiles
- copied systemd unit files with private paths

If secrets were ever committed, rotate them and clean Git history.

See also:
- `SECURITY.md`
- `CONTRIBUTING.md`

---

## Public GitHub checklist

Before publishing or sharing the repository:

1. remove private runtime files from tracking
2. verify `.env`, `data/`, `logs/`, `*.db`, `*.csv`, and `*.xlsx` are ignored
3. store only example profiles in the tracked repo
4. keep deployment-specific environment files outside the repository
5. enable GitHub secret scanning, branch protection, and Dependabot

---

## License

MIT
