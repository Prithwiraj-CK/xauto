# Codex reply sessions (1, 3, 8, 11 PM IST)

`com.sinclair.codex-replies` calls `run_codex_replies.sh` / `scheduled_run.py replies`.

1. Run `scan.py` for fresh candidates. A failed scan stops this session.
2. Codex follows `CODEX_REPLIES.md` and `REPLY_GUIDE.md`, using the scan and current voice references.
3. Save up to 10 drafts at 1 PM or up to 3 at later sessions under `out/scheduled/YYYY-MM-DD/replies-HH/`. Zero is valid.
4. Validate source IDs against the scan, text length and voice rules, then enqueue in `out/reply_queue.sqlite3`.
5. The separate reply worker publishes at random 30–60 minute intervals. Duplicate source IDs are skipped; later sessions append safely.
6. Send a concise Discord summary. No tap cards or manual posting step.

The evening daily tweet is independent and follows `CODEX_DRAFT.md` and `content/PLAN.md`.
