Check Telegram Bots Health via Telethon

### Two components
1. **User account** (Telethon) — sends `/start` to each monitored bot every 30 min, measures response time
2. **Health bot** (BotFather token) — handles `/health` command, sends status & reports to your group

### Files created
| File | Purpose |
|---|---|
| config.py | Loads `.env`, validates settings |
| storage.py | In-memory ping result storage |
| checker.py | User client that pings bots |
| bot.py | Bot client: `/health`, status & report messages |
| main.py | Entry point, runs both clients + scheduler loops |
| .env.example | Template for your credentials |

### Setup steps

1. **Copy and fill `.env`:**
   ```bash
   cp .env.example .env
   ```
   Fill in: `API_ID`, `API_HASH` (from https://my.telegram.org), `PHONE`, `BOT_TOKEN` (from @BotFather), `MONITORED_BOTS`, `GROUP_ID`

2. **Add the health bot to your target group**

3. **Run:**
   ```bash
   python main.py
   ```
   First run will prompt for the phone verification code (for the user account session). Subsequent runs use the saved session.

### What happens
- **Every 30 min** — pings all bots, sends to group:
  ```
  BOT — STATUS
  bot1 — 🟢
  bot2 — 🔴
  ```
- **At 4:00 and 18:00 UTC** — detailed 12h report:
  ```
  BOT — время ответа, сек (мин, сред, макс)
  bot1 — 0.5, 1.2, 5.0
  bot2 — н/д, н/д, н/д ⚠️ не ответил: 24/24
  ```
- **`/health` command** — does a **live ping** of all bots and responds with current status
