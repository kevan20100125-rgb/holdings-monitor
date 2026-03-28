from __future__ import annotations


class Notifier:
    channel_name = "base"

    def send(self, text: str) -> None:
        raise NotImplementedError
