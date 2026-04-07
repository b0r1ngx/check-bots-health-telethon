from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional


@dataclass
class PingResult:
    timestamp: datetime
    response_time: Optional[float]  # seconds; None when bot didn't respond
    success: bool


class Storage:
    def __init__(self) -> None:
        self._results: dict[str, list[PingResult]] = {}

    @staticmethod
    def _key(bot_username: str) -> str:
        return bot_username.lstrip("@").lower()

    def add_result(self, bot_username: str, result: PingResult) -> None:
        key = self._key(bot_username)
        self._results.setdefault(key, []).append(result)

    def get_latest(self, bot_username: str) -> Optional[PingResult]:
        results = self._results.get(self._key(bot_username), [])
        return results[-1] if results else None

    def get_results_since(
        self, bot_username: str, since: datetime
    ) -> list[PingResult]:
        return [
            r
            for r in self._results.get(self._key(bot_username), [])
            if r.timestamp >= since
        ]

    def cleanup(self, keep_hours: int = 24) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=keep_hours)
        for key in self._results:
            self._results[key] = [
                r for r in self._results[key] if r.timestamp >= cutoff
            ]
