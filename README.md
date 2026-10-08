# @SinClair_0000 X helper

Everything arrives in Discord with a one-tap link that opens X with the text filled in.
No X API, no X developer account. You press Post yourself.

- **Daily post** (Claude cloud routine, 1x/day, steps in `DAILY_POST.md`): Claude picks a post type
  from `content/PLAN.md` (pool research, safety breakdown, teaching, journey, question…), pulls live
  Meteora DLMM data, draws a chart for pool posts, writes the post → Discord "🚀 Post on X" + image.
- **Reply drafts** (Claude cloud routine, 4x/day, steps in `ROUTINE.md`): fresh Meteora/LP tweets →
  drafted replies → Discord "✍️ Reply on X".

Cost: twitterapi.io reads ~$2–3/month. Meteora + RugCheck data are free. Claude runs on your plan.

## Files

| file | what |
|---|---|
| `content/PLAN.md` | post types, mix, voice and rules: edit this to change what gets posted |
| `content/teaching_bank.json` | evergreen teaching posts Claude can use or adapt |
| `knowledge/lp-notes.md` | LP Army Academy + Meteora notes Claude writes from |
| `research.py` | `scan` top pools (fee/TVL, volume, safety) · `chart <address>` → `out/chart.png` |
| `history.py` | your recent tweets, so posts don't repeat |
| `send_post.py` / `send_discord.py` | send the daily post / reply drafts to Discord |
| `scan.py`, `REPLY_GUIDE.md`, `config/creators.txt` | reply helper |
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

## Cloud environment (claude.ai/code → Default environment)

- Network secret: twitterapi.io key, host `api.twitterapi.io`, header `X-API-Key`, no prefix
  (the proxy adds it; sessions never see it)
- Env var: `DISCORD_WEBHOOK_URL`
- Network access: `api.twitterapi.io`, `discord.com`, `dlmm.datapi.meteora.ag`, `api.dexscreener.com`,
  `api.rugcheck.xyz`,
  plus PyPI (for `pip install matplotlib`)

## Posting with an image

Discord shows the image above the link. On your phone: long-press the image → Save, tap
**Post on X**, tap the image icon in X, pick it, Post.

## Growth playbook

- **Referral**: Valhalla posts say `reply "ref"`. Send your link to whoever replies (by hand).
- **First 30 min after each post**: reply to every comment. Early replies are the biggest reach signal.
- **Wins**: post real PnL cards when you have one, with the setup. Occasionally post a loss.
- **Engage**: use the reply drafts. No shilling in replies; your profile does that.
