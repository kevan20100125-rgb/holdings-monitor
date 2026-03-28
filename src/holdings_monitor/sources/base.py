from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FetchResult:
    raw_bytes: bytes
    source_url: str
    snapshot_date: str


class SourceAdapter:
    def fetch(self) -> FetchResult:
        raise NotImplementedError

    def parse(self, raw_bytes: bytes):
        raise NotImplementedError
