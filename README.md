# @SinClair_0000 daily tweet bot

Posts 1 tweet/day from `content/queue.json` at 14:00 UTC via the official X API.
Cost: 30 posts x $0.015 = **~$0.45/month**. Hosting (GitHub Actions) is free.

## Setup (one time, ~15 min)

1. **X developer app**: developer.x.com → create a project + app → User authentication settings →
   permissions **Read and Write** → generate *API Key/Secret* and *Access Token/Secret*
   (regenerate the access token *after* switching to Read and Write). Add ~$5 credit.
2. **GitHub**: create a **private** repo, push this folder.
3. Repo → Settings → Secrets and variables → Actions → add:
   `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`
4. Actions tab → `daily-tweet` → **Run workflow** once to test. After that it runs daily.

Progress is saved in `content/state.json` (the workflow commits it back).

## Editing content

- Edit / reorder / append to `content/queue.json`. Entries with `"review": true` make claims
  about *your* setup (Valhalla, PnL rules): check they're true for you before they go out.
- Validate lengths: `CHECK=1 python3 post.py`
- Preview next post: `DRY_RUN=1 python3 post.py`
- **No links in queued tweets**: a link makes the post cost $0.20 instead of $0.015 and X
  shows link posts to fewer people. Send your referral link by hand to people who reply "ref".

## Growth playbook (the bot only does the posting)

- **Referral**: the Valhalla tweets say `reply "ref"`. Send your link to whoever replies
  (reply or DM by hand; free, and allowed because they asked).
- **First 30 min after each post**: reply to every comment. Early replies are the biggest reach signal.
- **Wins**: post real PnL cards manually from the app when you have one (free). Include the
  tx/setup; occasionally post a loss. Credibility is what makes the referral link convert.
- **Engage**: reply thoughtfully to Meteora / LP Army / DLMM creators a few times a day by hand.
  No shilling in replies; your profile does that.
- **Valhalla mentions**: max ~1 in 7 posts. More reads as an ad account.
- Turn on X's "Automated" label: Settings → Your account → Account information → Automation.
