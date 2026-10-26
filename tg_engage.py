"""One engagement round for a Telegram like-scroll group.

  python3 tg_engage.py                 -> runs one round against TG_ENGAGE_CHAT
  python3 tg_engage.py --chat <name>   -> override the chat (title substring)
  python3 tg_engage.py --dry           -> show what it would do, change nothing
  python3 tg_engage.py --count N       -> engage N tweets (default 10)

What one round does:
  1. Pull the latest ~50 messages from the chat
  2. Keep ones with an x.com/<handle>/status/<id> link that we HAVEN'T ❤️-reacted on yet
  3. For each (newest first, up to --count):
       - like the X tweet via x_actions.py (random 25-45s gap between likes)
       - if the like succeeds, react ❤️ on the Telegram message
       - if the like FAILS, stop — do not react (would be faking engagement)
  4. Post our latest Sinclair tweet URL into the chat (from X_BOT_LATEST_TWEET_URL, or --tweet-url)
  5. Print a summary and ping Discord with $ spent

Env (.env, gitignored): TG_API_ID, TG_API_HASH, TG_PHONE (from tg_setup.py),
TG_ENGAGE_CHAT (chat title substring, e.g. "10 LIKE SCROLL"),
X_BOT_LATEST_TWEET_URL (updated by post_today.py; or pass --tweet-url).
"""
import argparse
import asyncio
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji

ROOT = Path(__file__).parent
SESSION = ROOT / "out" / "telegram"
LOG = ROOT / "out" / "tg_engage_log.json"
HEART = "❤"  # the engagement group default

TWEET_RE = re.compile(r"https?://(?:x|twitter)\.com/[A-Za-z0-9_]+/status/(\d+)")


def load_env():
    f = ROOT / ".env"
    if f.exists():
        for l in f.read_text().splitlines():
            if "=" in l and not l.lstrip().startswith("#"):
                k, v = l.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def need(name):
    v = os.getenv(name)
    if not v:
        sys.exit(f"missing {name} in .env")
    return v


def log_round(entry):
    log = []
    if LOG.exists():
        try:
            log = json.loads(LOG.read_text())
        except ValueError:
            log = []
    log.append(entry)
    LOG.parent.mkdir(exist_ok=True)
    LOG.write_text(json.dumps(log, indent=2))


def like_on_x(tweet_id, dry):
    if dry:
        print(f"  [dry] would like tweet {tweet_id}")
        return True
    env = {**os.environ, "X_BOT_MIN_GAP_SEC": "0"}
    r = subprocess.run([sys.executable, str(ROOT / "x_actions.py"), "like", tweet_id],
                       env=env, capture_output=True, text=True)
    ok = r.returncode == 0 and "ok" in r.stdout
    print(f"  {'ok' if ok else 'FAIL'} like {tweet_id}  {r.stdout.strip()[:120]}  {r.stderr.strip()[:120]}")
    return ok


async def resolve_chat(client, title_sub):
    """Find the first dialog whose title contains title_sub (case-insensitive)."""
    async for d in client.iter_dialogs():
        if d.title and title_sub.lower() in d.title.lower():
            return d.entity
    sys.exit(f"no chat found with title containing '{title_sub}'")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", default=os.getenv("TG_ENGAGE_CHAT", "10 LIKE SCROLL"))
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--tweet-url", default=os.getenv("X_BOT_LATEST_TWEET_URL"))
    args = ap.parse_args()

    load_env()
    client = TelegramClient(str(SESSION), int(need("TG_API_ID")), need("TG_API_HASH"))
    await client.start(phone=need("TG_PHONE"))
    try:
        chat = await resolve_chat(client, args.chat)
        print(f"chat: {getattr(chat, 'title', chat.id)}")

        # Pull recent messages, newest first
        msgs = []
        async for m in client.iter_messages(chat, limit=60):
            msgs.append(m)
        print(f"scanned {len(msgs)} messages")

        candidates = []
        for m in msgs:
            text = m.message or ""
            tid_match = TWEET_RE.search(text)
            if not tid_match:
                # also scan link entities / url previews
                for e in (m.entities or []):
                    url = getattr(e, "url", None) or (text[e.offset:e.offset + e.length] if hasattr(e, "offset") else "")
                    tid_match = TWEET_RE.search(url or "")
                    if tid_match:
                        break
            if not tid_match:
                continue
            tid = tid_match.group(1)
            # already reacted by me?
            mine = False
            if m.reactions and m.reactions.recent_reactions:
                for r in m.reactions.recent_reactions:
                    if getattr(r, "my", False) or (hasattr(r, "peer_id") and getattr(r.peer_id, "user_id", None) == (await client.get_me()).id):
                        mine = True
            # fallback flag some Telegram versions set
            if m.reactions and getattr(m.reactions, "chosen", False):
                mine = True
            candidates.append({"mid": m.id, "tid": tid, "already_reacted": mine, "sender": getattr(m.sender, "username", None) or str(m.sender_id)})

        fresh = [c for c in candidates if not c["already_reacted"]][:args.count]
        print(f"candidates with x.com links: {len(candidates)}  fresh (not yet reacted): {len(fresh)}")
        if len(fresh) < args.count:
            print(f"  WARNING: only {len(fresh)} fresh, requested {args.count}")

        results = []
        for i, c in enumerate(fresh):
            if i > 0:
                gap = random.uniform(25, 45)
                print(f"  sleeping {gap:.1f}s before next like")
                await asyncio.sleep(gap)
            ok = like_on_x(c["tid"], args.dry)
            if ok and not args.dry:
                try:
                    await client(SendReactionRequest(peer=chat, msg_id=c["mid"],
                                                    reaction=[ReactionEmoji(emoticon=HEART)]))
                    print(f"  reacted ❤️ on telegram msg {c['mid']}")
                    results.append({**c, "liked": True, "reacted": True})
                except Exception as e:
                    print(f"  react FAILED on {c['mid']}: {e}")
                    results.append({**c, "liked": True, "reacted": False, "err": str(e)})
            elif args.dry and ok:
                print(f"  [dry] would react ❤️ on {c['mid']}")
                results.append({**c, "liked": True, "reacted": True})
            else:
                print(f"  stopping round: like failed on {c['tid']}, not reacting")
                results.append({**c, "liked": False, "reacted": False})
                break

        posted_our_tweet = False
        if args.tweet_url and not args.dry and all(r.get("reacted") for r in results) and len(results) == args.count:
            try:
                await client.send_message(chat, args.tweet_url)
                posted_our_tweet = True
                print(f"posted our tweet url: {args.tweet_url}")
            except Exception as e:
                print(f"posting our tweet FAILED: {e}")
        elif args.dry:
            print(f"[dry] would post our tweet url: {args.tweet_url}")

        log_round({"at": time.time(), "chat": getattr(chat, "title", str(chat.id)),
                   "results": results, "posted_our_tweet": posted_our_tweet, "dry": args.dry})
        print(f"\nround done: {sum(1 for r in results if r.get('liked'))} likes, "
              f"{sum(1 for r in results if r.get('reacted'))} reacts, "
              f"our tweet posted: {posted_our_tweet}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
