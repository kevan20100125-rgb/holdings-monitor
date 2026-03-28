from __future__ import annotations

import requests

from holdings_monitor.config import RuntimeSettings
from holdings_monitor.exceptions import NotifyError
from holdings_monitor.notify.base import Notifier

REQUEST_TIMEOUT = (15, 60)


class LineNotifier(Notifier):
    channel_name = "line"

    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        if not self.settings.line_channel_access_token:
            raise NotifyError("missing LINE_CHANNEL_ACCESS_TOKEN")
        if not self.settings.line_to_user_id:
            raise NotifyError("missing LINE_TO_USER_ID")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.line_channel_access_token}",
            "Content-Type": "application/json",
        }

    def _chunk_text(self, text: str, max_len: int = 4500) -> list[str]:
        if len(text) <= max_len:
            return [text]

        chunks: list[str] = []
        current: list[str] = []
        for line in text.splitlines():
            candidate = "\n".join(current + [line]).strip()
            if len(candidate) <= max_len:
                current.append(line)
            else:
                if current:
                    chunks.append("\n".join(current).strip())
                current = [line]

        if current:
            chunks.append("\n".join(current).strip())
        if len(chunks) > 5:
            chunks = chunks[:4] + ["⚠️ 訊息過長，後續內容已截斷。"]
        return chunks

    def verify(self) -> dict:
        url = f"https://api.line.me/v2/bot/profile/{self.settings.line_to_user_id}"
        response = requests.get(url, headers=self._headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            raise NotifyError(f"LINE verify failed: HTTP {response.status_code} | {response.text}")
        return response.json()

    def send(self, text: str) -> None:
        payload = {
            "to": self.settings.line_to_user_id,
            "messages": [{"type": "text", "text": chunk} for chunk in self._chunk_text(text)],
        }
        response = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=self._headers(),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            raise NotifyError(f"LINE push failed: HTTP {response.status_code} | {response.text}")
