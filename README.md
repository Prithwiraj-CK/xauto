# @SinClair_0000 X bot

At **9:31 PM IST**, `com.sinclair.codex-draft` runs Codex to research **today's** topic, validate the draft and immediately publish it through twitterapi.io. Research can take a few minutes. The 10:31 PM and 11:31 PM retries skip dates already posted. It uses `CODEX_DRAFT.md` and the weekly plan in `content/PLAN.md`. No next-day 1 PM daily-post job remains.

Separate Codex reply sessions run at **1 PM, 3 PM, 8 PM and 11 PM IST** (`com.sinclair.codex-replies`). They follow `CODEX_REPLIES.md` and `REPLY_GUIDE.md`: up to 10 replies at 1 PM and up to 3 at each other session; fewer or zero are fine. There is no extra five-reply batch attached to the evening post. Per-session drafts are stored under `out/scheduled/YYYY-MM-DD/replies-HH/`.

Replies go into a durable shared SQLite queue. `com.sinclair.reply-worker` checks it every five minutes, sends at random 30–60 minute intervals, prevents duplicate source IDs, and resumes queued work after restart. Failed items are retained as failed for inspection. The old Claude schedules remain paused. Discord receives summaries only.

The Mac must be awake, logged in and online for punctual execution. On wake, drafting uses the current IST date and latest eligible session; it does not publish yesterday's missed evening post in the morning.

| Day | Research and post topic |
|---|---|
| Monday | Viral Solana story and your take |
| Tuesday | Hot take / debate |
| Wednesday | Meteora research, teaching or news |
| Thursday | Another Meteora topic, different from Wednesday |
| Friday | Polymarket odds and news |
| Saturday | A different hot take / debate |
| Sunday | Personal lesson, question or next-week watchlist |

The documented breaking-news override requires a source URL and reason in `schedule_override`; the usual slot is enforced otherwise. First-person experiences must come from `content/journal.md`.


## Files

| file | what |
|---|---|
| `content/PLAN.md` | post types, mix, voice and rules: edit this to change what gets posted |
| `content/teaching_bank.json` | evergreen teaching posts the drafter can use or adapt |
| `knowledge/lp-notes.md` | LP Army Academy + Meteora notes for the drafter |
| `research.py` | `scan` top pools (fee/TVL, volume, safety) · `chart <address>` → `out/chart.png` |
| `history.py` | your recent tweets, so posts don't repeat |
| `run_daily.py` / `run_replies.py` | post the daily tweet and spaced replies |
| `scan.py`, `REPLY_GUIDE.md`, `config/creators.txt` | reply helper |
| `trends.py` | last 48h of Meteora / DLMM / LP Army talk for trend posts (budget-capped, max $0.10) |
| `spend.py` | twitterapi.io balance; each routine run posts its cost + balance to Discord, warns under $1 |
| `discover.py` | find & rank accounts posting about Meteora → `--apply` adds top 15 to `creators.txt` |
| `discord_reader.py` / `discord_user_reader.py` | allowlisted channel reader with bot Gateway and user REST modes |

## Reading Discord messages safely

`discord_reader.py` defaults to an official Discord application/bot account. The reader prints each
new message from the configured channels as one JSON record. It can optionally
append those records to a local JSONL file.

### Setup

1. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications).
2. Add a bot user and copy its bot token into `.env` as `DISCORD_BOT_TOKEN`.
3. Enable **Message Content Intent** under the bot's Privileged Gateway Intents.
4. Invite the bot with the `bot` scope and grant it `View Channel` and
   `Read Message History` in the target channels.
5. Copy `.env.example` to `.env`, set `DISCORD_CHANNEL_IDS`, and install the
   dependencies:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   cp .env.example .env
   ```

Run it with live messages only:

```bash
.venv/bin/python discord_reader.py
```

To read up to `DISCORD_HISTORY_LIMIT` existing messages once at startup:

```bash
.venv/bin/python discord_reader.py --history
```

Every message is restricted to the configured channel IDs and bot-authored
messages are ignored. Leave `DISCORD_MESSAGE_LOG` empty to avoid persisting
message content; set it only when local JSONL storage is intended.

### Read-only user mode

User mode polls only the configured guild channels using the account's
existing access. It only performs GET requests. Discord prohibits automated
user accounts and may terminate them; this mode is unsupported by Discord.
See [Discord's policy](https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots).

Set `DISCORD_AUTH=user`, `DISCORD_USER_TOKEN`, and the existing
`DISCORD_CHANNEL_IDS` in `.env`. User and bot tokens have separate fields;
tokens are never automatically reinterpreted or copied between them.
`DISCORD_POLL_SECONDS` defaults to 15 and must be at least 10. HTTP 429
responses wait for Discord's requested retry interval. Startup history is
opt-in (`--history`) and limited to the latest 100 messages per channel.

```bash
.venv/bin/python discord_reader.py --auth user --check
.venv/bin/python discord_reader.py --auth user
```

`--check` validates authentication and channel access without displaying
message content. Live mode paginates to catch up between polls and tracks
message IDs in memory to avoid duplicates; history is not persisted across
restarts. Thread IDs must be allowlisted explicitly. The existing X drafts
and webhook scripts run separately and are not fed by this reader.

## Local environment

Keep `TWITTERAPI_KEY`, `DISCORD_WEBHOOK_URL`, and `X_BOT_USERNAME` in the gitignored `.env`. The Codex CLI uses the local ChatGPT sign-in. `out/codex_draft.log` records the draft run and `out/run_daily.log` and `out/run_replies.log` record posting. The daily job validates and stamps the draft, publishes it, then commits and pushes the draft backup. Missing, stale or modified drafts are refused. A backup failure never causes a second post. Reply drafts are local and do not change the daily post files.

## Growth playbook

- **Referral**: Valhalla posts say `reply "ref"`. Send your link to whoever replies (by hand).
- **First 30 min after each post**: reply to every comment. Early replies are the biggest reach signal.
- **Wins**: post real PnL cards when you have one, with the setup. Occasionally post a loss.
- **Engage**: use the reply drafts. No shilling in replies; your profile does that.
