# Daily post (10:00 AM IST)

`com.sinclair.codex-draft` calls `run_codex_draft.sh` / `scheduled_run.py daily` at 9:15 AM IST to research today's weekday topic. It waits until 10:00 AM to publish, one hour before the selected MEGA ENGAGE session. The 9:45 and 10:00 AM retries skip dates already posted. A draft not ready by 10:15 AM is not published for that session.

Codex follows `CODEX_DRAFT.md` and `content/PLAN.md`. It may refresh `history.py`, `trends.py`, and `style.py`, within the $0.10 total twitterapi.io research cap.

On Wednesday or Thursday, if choosing a Meteora pool research post:
1. Run `python3 research.py scan` and inspect `out/pools.json`.
2. Choose a pool not covered recently; run `python3 research.py chart <address>`.
3. Use verified numbers from `out/chart_pool.json` and the authentic chart. Frame it as research, not a call to buy. Skip danger-rated pools for promotional research.

The scheduler validates type, voice, length and proof; stamps today's date and exact post hash; calls `run_daily.py --post-only`; then commits and pushes the draft backup. Failed publication does not write a successful daily stamp. The four reply sessions run independently.
