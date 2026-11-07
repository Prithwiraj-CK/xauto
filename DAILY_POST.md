# Daily post (1:00 PM IST)

`com.sinclair.codex-draft` calls `run_codex_draft.sh` / `scheduled_run.py daily` at 11 AM IST to research today's weekday topic. An early draft releases the shared research lock; the 12:59 PM trigger waits briefly to publish at 1 PM. Retries at 1, 1:30, 2 and 2:30 PM skip dates already posted. A draft not ready by 2:45 PM is not published. The actual successful post time starts the five-hour 10 LIKE SCROLL window, followed by the 8 PM MEGA session when it opens.

Codex follows `CODEX_DRAFT.md`, `content/PLAN.md` and the writing authority `content/VOICE.md`. It may refresh `history.py`, `trends.py`, and `style.py`, within the $0.10 total twitterapi.io research cap.

On Wednesday or Thursday, if choosing a Meteora pool research post:
1. Run `python3 research.py scan` and inspect `out/pools.json`.
2. Choose a pool not covered recently; run `python3 research.py chart <address>`.
3. Use verified numbers from `out/chart_pool.json` and the authentic chart. Frame it as research, not a call to buy. Skip danger-rated pools for promotional research.

The scheduler validates type, voice, length and proof; stamps today's date and exact post hash; calls `run_daily.py --post-only`; then commits and pushes the draft backup. Failed publication does not write a successful daily stamp. The four reply sessions run independently.

Drafts also follow `content/POST_SCHEMA.md`. Publication accepts a QT with images,
checks real @mentions and image provenance, then reads the live main tweet and source
reply back. `out/publications/` retains IDs before verification. If verification fails,
inspect that receipt and the existing post; never force a second publication. Uncertain
writes block replacement drafts until reviewed. No live test posts are needed for code changes.

The editorial pass must establish a contribution beyond the quoted source. The shared
contract rejects stored bad examples and the repeated short-opener/cautious-narrator/
audience-question formula before publication. These are regression checks, not a
guarantee of natural writing. If no worthwhile supported angle fits, fail the draft.
