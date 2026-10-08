# @SinClair_0000 X helper

Everything arrives in Discord with a one-tap link that opens X with the text filled in.
No X API, no X developer account. You press Post yourself.

- **Daily post** (Claude cloud routine, 1x/day, steps in `DAILY_POST.md`): Claude picks a post type
  from `content/PLAN.md` (pool research, safety breakdown, teaching, journey, question…), pulls live
  Meteora DLMM data, draws a chart for pool posts, writes the post → Discord "🚀 Post on X" + image.
- **Reply drafts** (Claude cloud routine, 4x/day, steps in `ROUTINE.md`): fresh Meteora/LP tweets →
  drafted replies → Discord "✍️ Reply on X".

Cost: twitterapi.io reads ~$1.50/month. Meteora + RugCheck data are free. Claude runs on your plan.

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
| `discover.py` | find & rank accounts posting about Meteora → `--apply` adds top 15 to `creators.txt` |

## Cloud environment (claude.ai/code → Default environment)

- Env vars: `TWITTERAPI_KEY`, `DISCORD_WEBHOOK_URL`
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
