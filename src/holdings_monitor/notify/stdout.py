from __future__ import annotations

from holdings_monitor.notify.base import Notifier


class StdoutNotifier(Notifier):
    channel_name = "stdout"

    def send(self, text: str) -> None:
        print(text)
