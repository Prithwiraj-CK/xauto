# Same-evening daily post (9:31 PM IST)

`com.sinclair.codex-draft` calls `run_codex_draft.sh` / `scheduled_run.py daily`. It researches today's IST weekday topic and publishes as soon as drafting and validation finish. Retries at 10:31 and 11:31 skip dates already posted. No next-day posting handoff.

Codex follows `CODEX_DRAFT.md` and `content/PLAN.md`. It may refresh `history.py`, `trends.py`, and `style.py`, within the $0.10 total twitterapi.io research cap.

On Wednesday, if choosing a Meteora pool research post:
1. Run `python3 research.py scan` and inspect `out/pools.json`.
2. Choose a pool not covered recently; run `python3 research.py chart <address>`.
3. Use verified numbers from `out/chart_pool.json` and the authentic chart. Frame it as research, not a call to buy. Skip danger-rated pools for promotional research.

The scheduler validates type, voice, length and proof; stamps today's date and exact post hash; calls `run_daily.py --post-only`; then commits and pushes the draft backup. Failed publication does not write a successful daily stamp. The four reply sessions run independently.
