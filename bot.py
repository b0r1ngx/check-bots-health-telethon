from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

from telethon import TelegramClient, events

import socks

from config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    GROUP_ID,
    ADMIN_IDS,
    MONITORED_BOTS,
    SESSIONS_DIR,
    PROXY_HOST,
    PROXY_PORT,
)
from storage import PingResult, Storage

if TYPE_CHECKING:
    from checker import HealthChecker

logger = logging.getLogger(__name__)


class HealthBot:
    """Telegram bot that exposes /health and sends scheduled reports."""

    def __init__(self, storage: Storage) -> None:
        self.client = TelegramClient(
            os.path.join(SESSIONS_DIR, "bot"), API_ID, API_HASH,
            proxy=(socks.SOCKS5, PROXY_HOST, PROXY_PORT, True),
        )
        self.storage = storage
        self.checker: HealthChecker | None = None  # injected after init

    async def start(self) -> None:
        await self.client.start(bot_token=BOT_TOKEN)
        me = await self.client.get_me()
        logger.info("Bot started as @%s", me.username)

        @self.client.on(events.NewMessage(pattern=r"/health(?:@\w+)?$"))
        async def _health_cmd(event):
            if ADMIN_IDS and event.sender_id not in ADMIN_IDS:
                return

            if self.checker is not None:
                msg = await event.respond("⏳ Проверяю ботов...")
                results = await self.checker.ping_all()
                await msg.edit(self._format_status(results))
            else:
                await event.respond(self._format_cached_status())

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------

    @staticmethod
    def _format_status(results: dict[str, PingResult]) -> str:
        lines = ["BOT — STATUS — время ответа, сек"]
        for bot_username, result in results.items():
            name = bot_username.lstrip("@")
            status = "🟢" if result.success else "🔴"
            rt = f"{result.response_time}" if result.response_time is not None else "—"
            lines.append(f"{name} — {status} — {rt}")
        return "\n".join(lines)

    def _format_cached_status(self) -> str:
        lines = ["BOT — STATUS — время ответа, сек"]
        for bot_username in MONITORED_BOTS:
            name = bot_username.lstrip("@")
            result = self.storage.get_latest(bot_username)
            if result is None:
                status = "⚪"  # never checked yet
                rt = "—"
            else:
                status = "🟢" if result.success else "🔴"
                rt = f"{result.response_time}" if result.response_time is not None else "—"
            lines.append(f"{name} — {status} — {rt}")
        return "\n".join(lines)

    def _build_detailed_report(self) -> str:
        since = datetime.now(timezone.utc) - timedelta(hours=12)
        lines = ["BOT — время ответа, сек (мин, сред, макс)"]

        for bot_username in MONITORED_BOTS:
            name = bot_username.lstrip("@")
            results = self.storage.get_results_since(bot_username, since)

            if not results:
                lines.append(f"{name} — нет данных")
                continue

            successful = [
                r for r in results if r.success and r.response_time is not None
            ]
            failed_count = sum(1 for r in results if not r.success)
            total = len(results)

            if successful:
                times = [r.response_time for r in successful]
                min_t = round(min(times), 1)
                avg_t = round(sum(times) / len(times), 1)
                max_t = round(max(times), 1)
                line = f"{name} — {min_t}, {avg_t}, {max_t}"
            else:
                line = f"{name} — н/д, н/д, н/д"

            if failed_count > 0:
                line += f" ⚠️ не ответил: {failed_count}/{total}"

            lines.append(line)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Scheduled senders
    # ------------------------------------------------------------------

    async def send_status_to_group(self, results: dict[str, PingResult]) -> None:
        if not GROUP_ID:
            return
        try:
            await self.client.send_message(GROUP_ID, self._format_status(results))
        except Exception as exc:
            logger.error("Failed to send status to group: %s", exc)

    async def send_detailed_report(self) -> None:
        if not GROUP_ID:
            return
        try:
            await self.client.send_message(GROUP_ID, self._build_detailed_report())
        except Exception as exc:
            logger.error("Failed to send detailed report: %s", exc)
