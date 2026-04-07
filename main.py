import asyncio
import logging
from datetime import datetime, timezone, timedelta

from config import PING_INTERVAL, REPORT_HOURS, MONITORED_BOTS
from storage import Storage
from checker import HealthChecker
from bot import HealthBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _next_report_time() -> datetime:
    """Return the nearest future report time (UTC)."""
    now = datetime.now(timezone.utc)
    candidates: list[datetime] = []
    for hour in REPORT_HOURS:
        candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        candidates.append(candidate)
    return min(candidates)


# ------------------------------------------------------------------
# Background loops
# ------------------------------------------------------------------

async def _ping_loop(checker: HealthChecker, bot: HealthBot) -> None:
    """Ping every PING_INTERVAL seconds and push a status message."""
    while True:
        try:
            logger.info("Ping cycle started for %d bot(s)", len(MONITORED_BOTS))
            results = await checker.ping_all()

            for username, res in results.items():
                st = "online" if res.success else "OFFLINE"
                rt = f"{res.response_time}s" if res.response_time is not None else "N/A"
                logger.info("  %s — %s (%s)", username, st, rt)

            await bot.send_status_to_group(results)
        except Exception as exc:
            logger.error("Ping loop error: %s", exc)

        await asyncio.sleep(PING_INTERVAL)


async def _report_loop(bot: HealthBot, storage: Storage) -> None:
    """Send a detailed 12-hour report at each configured UTC hour."""
    while True:
        target = _next_report_time()
        delay = (target - datetime.now(timezone.utc)).total_seconds()
        logger.info(
            "Next detailed report at %s UTC (in %.0f min)",
            target.strftime("%H:%M"),
            delay / 60,
        )
        await asyncio.sleep(max(delay, 0))

        try:
            await bot.send_detailed_report()
            storage.cleanup(keep_hours=24)
        except Exception as exc:
            logger.error("Report loop error: %s", exc)

        # avoid re-triggering on the same second
        await asyncio.sleep(60)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

async def main() -> None:
    storage = Storage()
    checker = HealthChecker(storage)
    health_bot = HealthBot(storage)

    # Start the user client first (may prompt for auth code on first run)
    await checker.start()
    await health_bot.start()

    # Let the bot call the checker for live /health pings
    health_bot.checker = checker

    logger.info(
        "Health monitoring active.  Tracking: %s", ", ".join(MONITORED_BOTS)
    )

    await asyncio.gather(
        checker.client.run_until_disconnected(),
        health_bot.client.run_until_disconnected(),
        _ping_loop(checker, health_bot),
        _report_loop(health_bot, storage),
    )


if __name__ == "__main__":
    asyncio.run(main())
