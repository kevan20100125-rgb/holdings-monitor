# holdings-monitor

A local holdings monitoring project that runs on Linux and can be scheduled with **systemd user services** and a **user timer**.

This project is intended to:
- run the holdings monitor manually for one-shot execution,
- schedule it periodically with `systemd --user`,
- keep the workflow isolated inside a Conda environment,
- make troubleshooting reproducible through `systemctl` and `journalctl`.

---

## 1. Environment

This project was operated in a Conda environment:

```bash
conda activate holdings-monitor
```

Recommended platform:
- Ubuntu / Linux desktop
- `systemd --user`
- Conda-managed Python environment

---

## 2. Project structure

A typical structure is:

```text
holdings-monitor/
├── README.md
├── src/                     # source code
├── requirements.txt         # optional dependency list
└── systemd/
    ├── holdings-monitor.service
    └── holdings-monitor.timer
```

If your repository structure differs, adjust the paths in the systemd unit files accordingly.

---

## 3. Running the project manually

Before using the timer, first verify that the monitor can run manually.

Example:

```bash
conda activate holdings-monitor
cd ~/Programming_linux/holdings-monitor
python main.py
```

If your entry file is not `main.py`, replace it with the actual command used by your project.

This step matters because if the project cannot run manually, the systemd service will also fail.

---

## 4. systemd user service and timer

This project is configured as a **user-level** systemd task rather than a system-wide service.

Useful commands:

```bash
systemctl --user daemon-reload
systemctl --user enable --now holdings-monitor.timer
systemctl --user start holdings-monitor.service
systemctl --user status holdings-monitor.service
```

What they do:
- `daemon-reload`: reloads unit definitions after editing `.service` or `.timer`
- `enable --now ...timer`: enables the timer at login and starts it immediately
- `start ...service`: triggers a one-time run of the job
- `status ...service`: checks whether the run succeeded or failed

---

## 5. Observed execution result during setup

During setup, the following behavior was observed:

```bash
systemctl --user daemon-reload
systemctl --user enable --now holdings-monitor.timer
systemctl --user start holdings-monitor.service
systemctl --user status holdings-monitor.service
```

The service failed with an exit code:

```text
Job for holdings-monitor.service failed because the control process exited with error code.
See "systemctl --user status holdings-monitor.service" and "journalctl --user -xeu holdings-monitor.service" for details.
× holdings-monitor.service - Run holdings-monitor once
     Loaded: loaded (/home/kevan/.config/systemd/user/holdings-monitor.service; static)
     Active: failed (Result: exit-code)
```

This means the timer was registered, but the actual service command did not complete successfully.

---

## 6. How to debug a failed service

When the service fails, use the following commands:

```bash
systemctl --user status holdings-monitor.service
journalctl --user -xeu holdings-monitor.service
```

Check for these common problems:

### 6.1 Wrong `ExecStart`
The command inside the service file may point to:
- the wrong Python executable,
- the wrong script path,
- a file that is not executable,
- or a working directory mismatch.

A reliable pattern is to use absolute paths inside the service file, for example:

```ini
ExecStart=/home/kevan/miniconda3/envs/holdings-monitor/bin/python /home/kevan/Programming_linux/holdings-monitor/main.py
```

### 6.2 Conda environment not loaded in systemd
A terminal session may know your Conda environment, but `systemd` does not automatically inherit that interactive shell state.

So the service should call the Python binary inside the target Conda environment directly.

### 6.3 Wrong working directory
If your script depends on relative paths, add:

```ini
WorkingDirectory=/home/kevan/Programming_linux/holdings-monitor
```

### 6.4 Missing permissions
If the script reads local files such as config, CSV, logs, or credentials, verify that the user account running the service has access.

### 6.5 Program runs in terminal but fails in service mode
This usually means the script depends on shell-specific state such as:
- activated Conda environment,
- environment variables,
- current working directory,
- user-specific PATH,
- or manually exported secrets.

In that case, define them explicitly in the service file.

---

## 7. Example service file

Below is a reference template for `~/.config/systemd/user/holdings-monitor.service`:

```ini
[Unit]
Description=Run holdings-monitor once
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/kevan/Programming_linux/holdings-monitor
ExecStart=/home/kevan/miniconda3/envs/holdings-monitor/bin/python /home/kevan/Programming_linux/holdings-monitor/main.py
Restart=no

[Install]
WantedBy=default.target
```

If your script file is different, replace `main.py` with the actual entry point.

---

## 8. Example timer file

Reference template for `~/.config/systemd/user/holdings-monitor.timer`:

```ini
[Unit]
Description=Run holdings-monitor periodically

[Timer]
OnBootSec=1min
OnUnitActiveSec=30min
Unit=holdings-monitor.service

[Install]
WantedBy=timers.target
```

This example means:
- run once about 1 minute after login/boot,
- then rerun every 30 minutes after the previous activation.

---

## 9. Reloading after modification

Whenever the `.service` or `.timer` file is changed, run:

```bash
systemctl --user daemon-reload
systemctl --user restart holdings-monitor.timer
```

To test one-shot execution again:

```bash
systemctl --user start holdings-monitor.service
systemctl --user status holdings-monitor.service
```

---

## 10. Recommended verification checklist

Before considering the setup complete, verify:

```bash
conda activate holdings-monitor
cd ~/Programming_linux/holdings-monitor
python main.py
```

Then verify systemd:

```bash
systemctl --user daemon-reload
systemctl --user enable --now holdings-monitor.timer
systemctl --user list-timers --all | grep holdings-monitor
systemctl --user start holdings-monitor.service
systemctl --user status holdings-monitor.service
journalctl --user -u holdings-monitor.service -n 50 --no-pager
```

What success looks like:
- the timer appears in `list-timers`,
- the service exits cleanly,
- logs show the script executed as expected,
- repeated runs occur according to the timer policy.

---

## 11. Git and submission note

If this project is part of an assignment or portfolio repository, update and push again **only if**:
- you changed the README,
- you fixed the service/timer files,
- or you corrected setup instructions so others can reproduce the project.

If nothing changed in the repository, another push is unnecessary.

A README update is worth including because it documents:
- how the project is actually executed,
- how the timer is enabled,
- what failure was encountered,
- and how the issue should be debugged.

---

## 12. Current status summary

Based on the recorded setup process:
- the Conda environment was used successfully,
- the user-level timer was enabled,
- the user-level service was invoked manually,
- the service currently fails with `Result: exit-code`,
- so the remaining work is not timer registration but fixing the actual service command/runtime environment.

In other words, the scheduling layer is mostly in place; the failure is in the command execution path.

