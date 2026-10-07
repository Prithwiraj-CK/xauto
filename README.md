# @SinClair_0000 X helper

Everything arrives in Discord with a one-tap link that opens X with the text filled in.
No X API, no X developer account. You press Post yourself.

- **Daily tweet** (`post.py`, GitHub Actions, 14:00 UTC / 7:30 PM IST): next tweet from
  `content/queue.json` → Discord "🚀 Post on X".
- **Reply drafts** (`scan.py` → Claude → `send_discord.py`, Claude cloud routine, 4x/day): fresh
  Meteora/LP tweets → drafted replies → Discord "✍️ Reply on X". Steps in `ROUTINE.md`.

Cost: twitterapi.io reads ~$1.50/month. Everything else is free.

## Setup

1. Discord: Server Settings → Integrations → Webhooks → New Webhook → copy URL.
2. GitHub repo → Settings → Secrets and variables → Actions → add `DISCORD_WEBHOOK_URL`.
3. GitHub repo → Settings → Actions → General → Workflow permissions → **Read and write**
   (so it can save progress in `content/state.json`).
4. Actions tab → `daily-tweet` → **Run workflow** once to test. After that it runs daily.
5. Reply helper: claude.ai/code cloud environment → env vars `TWITTERAPI_KEY`,
   `DISCORD_WEBHOOK_URL`; network access allows `api.twitterapi.io` and `discord.com`.

## Editing content

- Edit / reorder / append to `content/queue.json`. Entries with `"review": true` make claims
  about *your* setup (Valhalla, PnL rules): check they're true for you before they go out.
- Validate lengths: `CHECK=1 python3 post.py`
- Preview next post: `DRY_RUN=1 python3 post.py`
- **No links in queued tweets**: X shows link posts to fewer people. Send your referral link by hand to people who reply "ref".

## Growth playbook

- **Referral**: the Valhalla tweets say `reply "ref"`. Send your link to whoever replies
  (reply or DM by hand; free, and allowed because they asked).
- **First 30 min after each post**: reply to every comment. Early replies are the biggest reach signal.
- **Wins**: post real PnL cards manually from the app when you have one (free). Include the
  tx/setup; occasionally post a loss. Credibility is what makes the referral link convert.
- **Engage**: reply thoughtfully to Meteora / LP Army / DLMM creators a few times a day by hand.
  No shilling in replies; your profile does that.
- **Valhalla mentions**: max ~1 in 7 posts. More reads as an ad account.
