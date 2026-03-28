# holdings-monitor

A small Linux-friendly project for tracking fund holdings changes, saving historical snapshots, comparing new data with previous snapshots, and optionally sending notifications.

This README is written for end users and first-time deployers. It is based on the current codebase and on a real `systemd --user` deployment issue encountered during setup.

---

## What this project does

`holdings-monitor` can:

- fetch a holdings export from a configured source,
- validate the downloaded data,
- store snapshots in SQLite,
- compare the latest snapshot with the previous one,
- print or send notifications when changes are detected,
- run manually or on a schedule through **systemd user services**.

The main CLI entrypoint in this repository is:

```bash
holdings-monitor run
```

or equivalently:

```bash
python -m holdings_monitor.cli run
```

---

## Project layout

Important paths in this repository:

```text
holdings-monitor/
├── configs/
│   └── profiles/
│       ├── examples/
│       └── local/
├── data/
├── deploy/
│   └── systemd/
│       ├── README.md
│       ├── holdings-monitor.env.example
│       ├── holdings-monitor.service.example
│       ├── holdings-monitor.timer.example
│       └── run_randomized_monitor.sh
├── logs/
├── scripts/
│   └── run_once.sh
├── src/
│   └── holdings_monitor/
├── tests/
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Requirements

Recommended environment:

- Linux desktop or server
- `systemd --user`
- Conda
- Python 3.11+ (the repo currently supports `>=3.11`)

---

## 1. Create the Conda environment

```bash
conda create -n holdings-monitor python=3.12 -y
conda activate holdings-monitor
```

Install the project in editable mode:

```bash
python -m pip install -e .[dev]
```

This installs the CLI command:

```bash
holdings-monitor
```

You can verify it with:

```bash
holdings-monitor --help
```

---

## 2. Prepare a profile

This project needs a profile YAML file that defines the source, validation rules, diff rules, and notification channels.

A local example already exists in this repository:

```text
configs/profiles/local/my-profile.yaml
```

If you want to start from the example profile:

```bash
cp configs/profiles/examples/upamc-00981A.yaml configs/profiles/local/my-profile.yaml
```

---

## 3. Prepare environment variables

There are **two common places** where environment variables are used in this repo:

1. project-level `.env`
2. systemd-specific env file at `~/.config/holdings-monitor/holdings-monitor.env`

### 3.1 Project `.env`

You can start from:

```bash
cp .env.example .env
```

Typical values:

```dotenv
HOLDINGS_MONITOR_ENV=development
HOLDINGS_MONITOR_PROFILE=configs/profiles/local/my-profile.yaml
HOLDINGS_MONITOR_DATA_DIR=data
HOLDINGS_MONITOR_LOG_DIR=logs
HOLDINGS_MONITOR_DB_PATH=data/holdings_monitor.db
HOLDINGS_MONITOR_LOG_LEVEL=INFO
HOLDINGS_MONITOR_TIMEZONE=Asia/Taipei
PYTHONNOUSERSITE=1
```

### 3.2 systemd env file

Create the directory and copy the example:

```bash
mkdir -p ~/.config/holdings-monitor
cp deploy/systemd/holdings-monitor.env.example ~/.config/holdings-monitor/holdings-monitor.env
```

Then edit:

```bash
nano ~/.config/holdings-monitor/holdings-monitor.env
```

At minimum, set these correctly:

```dotenv
HOLDINGS_MONITOR_PROJECT_ROOT=/home/your-user/path/to/holdings-monitor
HOLDINGS_MONITOR_PYTHON_BIN=/home/your-user/miniconda3/envs/holdings-monitor/bin/python
HOLDINGS_MONITOR_PROFILE=configs/profiles/local/my-profile.yaml
```

Recommended optional values:

```dotenv
HOLDINGS_MONITOR_DATA_DIR=data
HOLDINGS_MONITOR_LOG_DIR=logs
HOLDINGS_MONITOR_DB_PATH=data/holdings_monitor.db
HOLDINGS_MONITOR_LOG_LEVEL=INFO
HOLDINGS_MONITOR_TIMEZONE=Asia/Taipei
HOLDINGS_MONITOR_RANDOM_DELAY_MAX_SECONDS=5400
HOLDINGS_MONITOR_LOCK_FILE=/tmp/holdings-monitor.lock
PYTHONNOUSERSITE=1
```

---

## 4. Run the monitor manually first

Before using `systemd`, make sure the project works in a normal shell.

From the project root:

```bash
conda activate holdings-monitor
holdings-monitor run --profile configs/profiles/local/my-profile.yaml
```

Or:

```bash
python -m holdings_monitor.cli run --profile configs/profiles/local/my-profile.yaml
```

If you only want a one-shot wrapper script:

```bash
bash scripts/run_once.sh
```

If the manual run fails, fix that first. A `systemd` service will not succeed if the same command already fails in the terminal.

---

## 5. Deploy with systemd user service and timer

This repo already includes example unit files.

Copy them into your user systemd directory:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/systemd/holdings-monitor.service.example ~/.config/systemd/user/holdings-monitor.service
cp deploy/systemd/holdings-monitor.timer.example ~/.config/systemd/user/holdings-monitor.timer
```

Then reload and enable the timer:

```bash
systemctl --user daemon-reload
systemctl --user enable --now holdings-monitor.timer
```

To trigger one run immediately:

```bash
systemctl --user start holdings-monitor.service
```

To inspect status:

```bash
systemctl --user status holdings-monitor.service
systemctl --user status holdings-monitor.timer
```

To inspect timers:

```bash
systemctl --user list-timers --all | grep holdings-monitor
```

---

## 6. How the provided systemd setup works

### Service file

The example service uses:

```ini
EnvironmentFile=%h/.config/holdings-monitor/holdings-monitor.env
ExecStart=/usr/bin/env bash -lc '"$HOLDINGS_MONITOR_PROJECT_ROOT"/deploy/systemd/run_randomized_monitor.sh'
```

This means:

- `systemd` loads variables from `~/.config/holdings-monitor/holdings-monitor.env`
- it runs the helper script `deploy/systemd/run_randomized_monitor.sh`
- that helper script:
  - reads the project `.env` if present,
  - creates a lock file to avoid overlapping runs,
  - waits a random number of seconds,
  - runs the CLI with the Python binary you specified.

### Timer file

The example timer runs daily at 18:00:

```ini
[Timer]
OnCalendar=*-*-* 18:00:00
Persistent=true
Unit=holdings-monitor.service
```

`Persistent=true` means missed runs can be triggered later when the user session returns.

---

## 7. Important note about `static` in service status

You may see output like this:

```text
Loaded: loaded (.../holdings-monitor.service; static)
```

This is **not automatically an error**.

In this repository, the service file does **not** contain an `[Install]` section, so it is normal for the service to be shown as **static**. The timer is the unit that should be enabled.

What matters is whether the service exits successfully.

---

## 8. Real deployment issue encountered during setup

A real failure from the deployment logs looked like this:

```text
Job for holdings-monitor.service failed because the control process exited with error code.
See "systemctl --user status holdings-monitor.service" and "journalctl --user -xeu holdings-monitor.service" for details.
```

The project log then showed this earlier root cause:

```text
FileNotFoundError: [Errno 2] No such file or directory
```

That traceback happened while resolving:

```text
HOLDINGS_MONITOR_PROJECT_ROOT
```

### What this means

The service was able to start the wrapper script, but the project root path configured in the environment was invalid or did not exist from `systemd`'s point of view.

### Practical fix

Open the systemd env file:

```bash
nano ~/.config/holdings-monitor/holdings-monitor.env
```

Make sure this path is correct and actually exists:

```dotenv
HOLDINGS_MONITOR_PROJECT_ROOT=/home/kevan/Programming_linux/holdings-monitor
```

Then verify:

```bash
ls /home/kevan/Programming_linux/holdings-monitor
```

Also verify the Python binary path:

```bash
ls /home/kevan/miniconda3/envs/holdings-monitor/bin/python
```

After fixing the values:

```bash
systemctl --user daemon-reload
systemctl --user restart holdings-monitor.timer
systemctl --user start holdings-monitor.service
```

---

## 9. Another observed behavior: run succeeded after the path fix

Later logs showed a successful run:

```text
[start] sleeping 0s before monitor run
[run] starting monitor
... fetching source url=...
[done] monitor finished successfully
```

This indicates that the overall deployment pattern is valid once:

- the project root is correct,
- the Conda Python path is correct,
- the profile path is correct,
- dependencies are installed.

---

## 10. Fast troubleshooting checklist

When the service fails, run these commands first:

```bash
systemctl --user status holdings-monitor.service
journalctl --user -xeu holdings-monitor.service
journalctl --user -u holdings-monitor.service -n 100 --no-pager
```

Then also check the project-side runner log:

```bash
tail -n 100 logs/systemd-monitor.log
```

Things to verify:

### A. Project root exists

```bash
echo "$HOLDINGS_MONITOR_PROJECT_ROOT"
ls "$HOLDINGS_MONITOR_PROJECT_ROOT"
```

### B. Conda Python path exists

```bash
echo "$HOLDINGS_MONITOR_PYTHON_BIN"
ls "$HOLDINGS_MONITOR_PYTHON_BIN"
```

### C. The package is installed in that environment

```bash
/home/your-user/miniconda3/envs/holdings-monitor/bin/python -m pip show holdings-monitor
```

### D. The selected profile exists

```bash
ls /home/your-user/path/to/holdings-monitor/configs/profiles/local/my-profile.yaml
```

### E. The command works outside systemd

```bash
cd /home/your-user/path/to/holdings-monitor
/home/your-user/miniconda3/envs/holdings-monitor/bin/python -m holdings_monitor.cli run --profile configs/profiles/local/my-profile.yaml
```

If E fails, `systemd` is not the main problem.

---

## 11. Common reasons a user-level systemd service fails

### 1. Wrong `HOLDINGS_MONITOR_PROJECT_ROOT`
This was the main real issue observed in deployment.

### 2. Wrong `HOLDINGS_MONITOR_PYTHON_BIN`
`systemd` does not know which Conda environment you activated interactively. Always point to the exact Python executable inside the environment.

### 3. Wrong profile path
If `HOLDINGS_MONITOR_PROFILE` is wrong, the monitor cannot load the YAML config.

### 4. Missing dependencies
If `pandas`, `openpyxl`, `requests`, `PyYAML`, or `python-dotenv` are not installed in the selected environment, the service will fail.

### 5. Relative-path confusion
This repository resolves many paths relative to `HOLDINGS_MONITOR_PROJECT_ROOT`. If that root is wrong, several other paths fail too.

### 6. Permissions or session issues
The user running `systemd --user` must have permission to access the repo, logs, database, and lock file.

---

## 12. Testing without waiting for the daily timer

Because the default timer is daily at 18:00 and the wrapper script may add a random delay, testing can feel slow.

For test deployments:

1. trigger the service directly,
2. temporarily reduce the random delay in `~/.config/holdings-monitor/holdings-monitor.env`.

Example:

```dotenv
HOLDINGS_MONITOR_RANDOM_DELAY_MAX_SECONDS=1
```

Then reload and rerun:

```bash
systemctl --user daemon-reload
systemctl --user start holdings-monitor.service
```

Do **not** set the delay to `0` unless you also change the script, because the current shell code computes:

```bash
DELAY=$((RANDOM % MAX_DELAY_SECONDS))
```

and modulo by zero will fail.

---

## 13. Keep the timer active after logout

If you want the user timer to keep working even when you are not actively logged in:

```bash
loginctl enable-linger "$USER"
```

---

## 14. Useful commands summary

### Manual run

```bash
conda activate holdings-monitor
holdings-monitor run --profile configs/profiles/local/my-profile.yaml
```

### Deploy systemd files

```bash
mkdir -p ~/.config/holdings-monitor
cp deploy/systemd/holdings-monitor.env.example ~/.config/holdings-monitor/holdings-monitor.env

mkdir -p ~/.config/systemd/user
cp deploy/systemd/holdings-monitor.service.example ~/.config/systemd/user/holdings-monitor.service
cp deploy/systemd/holdings-monitor.timer.example ~/.config/systemd/user/holdings-monitor.timer
```

### Enable timer

```bash
systemctl --user daemon-reload
systemctl --user enable --now holdings-monitor.timer
```

### Run once immediately

```bash
systemctl --user start holdings-monitor.service
```

### Check logs

```bash
systemctl --user status holdings-monitor.service
journalctl --user -xeu holdings-monitor.service
journalctl --user -u holdings-monitor.service -n 100 --no-pager
tail -n 100 logs/systemd-monitor.log
```

---

## 15. Recommended first-time deployment flow

Use this order:

1. clone the repo,
2. create and activate the Conda environment,
3. install the package with `python -m pip install -e .[dev]`,
4. prepare a valid profile,
5. confirm `holdings-monitor run` works manually,
6. create `~/.config/holdings-monitor/holdings-monitor.env`,
7. copy the systemd example files,
8. run `systemctl --user daemon-reload`,
9. start the service once manually,
10. only then enable or trust the timer.

That order avoids most deployment confusion.

---

## 16. Final recommendation

If you see this again:

```text
Job for holdings-monitor.service failed because the control process exited with error code.
```

do not focus first on `static` in the service status.

Focus on these three values instead:

- `HOLDINGS_MONITOR_PROJECT_ROOT`
- `HOLDINGS_MONITOR_PYTHON_BIN`
- `HOLDINGS_MONITOR_PROFILE`

In this codebase, those are the highest-probability causes of user-level deployment failure.
