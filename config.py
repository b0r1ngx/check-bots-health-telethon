import os

from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

MONITORED_BOTS: list[str] = []
for _b in os.getenv("MONITORED_BOTS", "").split(","):
    _b = _b.strip()
    if _b:
        if not _b.startswith("@"):
            _b = f"@{_b}"
        MONITORED_BOTS.append(_b)

_group_raw = os.getenv("GROUP_ID", "")
try:
    GROUP_ID: int | str = int(_group_raw)
except ValueError:
    GROUP_ID = _group_raw  # could be @username for public groups

ADMIN_IDS: list[int] = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]

PING_INTERVAL = int(os.getenv("PING_INTERVAL", "1800"))  # seconds
PING_TIMEOUT = int(os.getenv("PING_TIMEOUT", "30"))  # seconds
REPORT_HOURS: list[int] = [
    int(h.strip()) for h in os.getenv("REPORT_HOURS", "4,18").split(",") if h.strip()
]

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)
