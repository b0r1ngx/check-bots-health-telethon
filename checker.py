import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

from telethon import TelegramClient, events

from config import API_ID, API_HASH, PHONE, PING_TIMEOUT, MONITORED_BOTS, SESSIONS_DIR
from storage import PingResult, Storage

logger = logging.getLogger(__name__)


class HealthChecker:
    """Pings monitored bots from a real Telegram user account."""

    def __init__(self, storage: Storage) -> None:
        self.client = TelegramClient(
            os.path.join(SESSIONS_DIR, "user"), API_ID, API_HASH
        )
        self.storage = storage
        self._pending: dict[str, asyncio.Event] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def start(self) -> None:
        await self.client.start(phone=PHONE)
        me = await self.client.get_me()
        logger.info("User client authorised as @%s", me.username or me.id)

        @self.client.on(events.NewMessage(incoming=True))
        async def _on_bot_reply(event):
            sender = await event.get_sender()
            if not sender:
                return
            if not getattr(sender, "bot", False):
                return
            username = getattr(sender, "username", None)
            if not username:
                return
            key = username.lower()
            evt = self._pending.get(key)
            if evt is not None:
                evt.set()

    async def ping_bot(self, bot_username: str) -> PingResult:
        key = bot_username.lstrip("@").lower()

        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        async with self._locks[key]:
            evt = asyncio.Event()
            self._pending[key] = evt

            start = time.monotonic()
            try:
                await self.client.send_message(bot_username, "/start")
                await asyncio.wait_for(evt.wait(), timeout=PING_TIMEOUT)
                elapsed = round(time.monotonic() - start, 3)
                result = PingResult(datetime.now(timezone.utc), elapsed, True)
            except asyncio.TimeoutError:
                result = PingResult(datetime.now(timezone.utc), None, False)
                logger.warning("Ping timeout: %s", bot_username)
            except Exception as exc:
                result = PingResult(datetime.now(timezone.utc), None, False)
                logger.error("Ping error for %s: %s", bot_username, exc)
            finally:
                self._pending.pop(key, None)

        self.storage.add_result(bot_username, result)
        return result

    async def ping_all(self) -> dict[str, PingResult]:
        async def _do(bot: str) -> tuple[str, PingResult]:
            return bot, await self.ping_bot(bot)

        pairs = await asyncio.gather(*[_do(b) for b in MONITORED_BOTS])
        return dict(pairs)
