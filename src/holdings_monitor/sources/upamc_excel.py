from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from holdings_monitor.config import ProfileConfig
from holdings_monitor.domain.models import HoldingRecord
from holdings_monitor.exceptions import FetchError
from holdings_monitor.sources.base import FetchResult, SourceAdapter
from holdings_monitor.sources.parsing import parse_holdings_excel

LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = (15, 60)
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 holdings-monitor/0.1"
)


@dataclass
class UpamcExcelSource(SourceAdapter):
    profile: ProfileConfig

    def __post_init__(self) -> None:
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "*/*",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
                "Referer": self.profile.source.export_url,
            }
        )
        return session

    def fetch(self) -> FetchResult:
        url = self.profile.source.export_url
        LOGGER.info("fetching source url=%s", url)
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except Exception as exc:
            raise FetchError(f"failed to fetch source: {exc}") from exc

        snapshot_date, _ = parse_holdings_excel(
            response.content, currency=self.profile.storage.currency
        )
        return FetchResult(raw_bytes=response.content, source_url=url, snapshot_date=snapshot_date)

    def parse(self, raw_bytes: bytes) -> tuple[str, list[HoldingRecord]]:
        return parse_holdings_excel(raw_bytes, currency=self.profile.storage.currency)
