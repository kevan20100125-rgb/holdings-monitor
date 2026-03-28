# systemd deployment

This directory contains **example** files for running `holdings-monitor` with a user-level systemd timer.

## Files

- `run_randomized_monitor.sh`: runner script with random delay and lock protection
- `holdings-monitor.service.example`: example user service
- `holdings-monitor.timer.example`: example user timer
- `holdings-monitor.env.example`: example environment file

## Recommended setup

1. Clone the repository to a stable path, for example:

   ```bash
   git clone <your-repo-url> ~/holdings-monitor
   cd ~/holdings-monitor
   ```

2. Create and activate a Python environment, then install the project:

   ```bash
   conda create -n holdings-monitor python=3.12 -y
   conda activate holdings-monitor
   python -m pip install -e .[dev]
   ```

3. Create a local profile:

   ```bash
   mkdir -p configs/profiles/local
   cp configs/profiles/examples/upamc-00981A.yaml configs/profiles/local/my-profile.yaml
   ```

4. Create the systemd environment directory and copy the example file:

   ```bash
   mkdir -p ~/.config/holdings-monitor
   cp deploy/systemd/holdings-monitor.env.example ~/.config/holdings-monitor/holdings-monitor.env
   ```

5. Edit `~/.config/holdings-monitor/holdings-monitor.env` and set at least:
   - `HOLDINGS_MONITOR_PROJECT_ROOT`
   - `HOLDINGS_MONITOR_PYTHON_BIN`
   - `HOLDINGS_MONITOR_PROFILE`

6. Copy the unit files:

   ```bash
   mkdir -p ~/.config/systemd/user
   cp deploy/systemd/holdings-monitor.service.example ~/.config/systemd/user/holdings-monitor.service
   cp deploy/systemd/holdings-monitor.timer.example ~/.config/systemd/user/holdings-monitor.timer
   ```

7. Reload and enable:

   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now holdings-monitor.timer
   ```

8. Test one manual run:

   ```bash
   systemctl --user start holdings-monitor.service
   systemctl --user status holdings-monitor.service
   journalctl --user -u holdings-monitor.service -n 100 --no-pager
   ```

## Keep timer active after logout

For long-term unattended runs:

```bash
loginctl enable-linger "$USER"
```

## Notes

- The timer triggers at `18:00`, then the runner script sleeps for a random delay.
- Random delay is controlled by `HOLDINGS_MONITOR_RANDOM_DELAY_MAX_SECONDS`.
- A lock file prevents overlapping runs.
- The script also writes to `logs/systemd-monitor.log` under the project root.
