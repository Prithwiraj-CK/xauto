"""Auto-post drafted replies from out/drafts.json via x_actions.py with random 30-60 min gaps.
Legacy name kept so anything invoking `python3 send_discord.py` still works.
The webhook now only receives a short ✅ summary of what was queued; no tap-cards.

Env: DISCORD_WEBHOOK_URL (summary only), TWITTERAPI_KEY (via x_actions)
     DRY_RUN=1  -> print what would happen, change nothing
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
DRAFTS = ROOT / "out" / "drafts.json"
PENDING = ROOT / "out" / "pending_replies.json"
MAX_CHARS = 100
AI_TELLS = ["great point", "love this", "this is huge", "here's the thing", "that said", "moreover",
            "worth noting", "not just", "game changer", "game-changer", "couldn't agree more", "spot on",
            "the real alpha", "this is why", "imagine", "a monkey that", "one that", "the kind of"]


def lint(reply):
    low, why = reply.lower(), []
    if len(reply) > MAX_CHARS:
        why.append(f"{len(reply)} chars (max {MAX_CHARS})")
    if any(c in reply for c in "—–;"):
        why.append("dash or semicolon")
    if reply.count(",") > 1 or re.search(r",[^,]*\band\b", low):
        why.append("list")
    if len(re.findall(r"[.!?]\s+\S", reply.strip())) > 1:
        why.append("3+ sentences")
    if "#" in reply or "http" in low:
        why.append("hashtag or link")
    why += [f'"{t}"' for t in AI_TELLS if t in low]
    if low.startswith("absolutely"):
        why.append('"absolutely"')
    return why


def humanize(reply):
    r = reply.strip().rstrip(".")
    return r[0].lower() + r[1:] if len(r) > 1 and r[0].isupper() and not r[1].isupper() else r


# Kept so spend.py / run_daily.py / engage_page.py still import these without breaking:
def buttons(*a, **k):
    return []


def send(payload, files=()):
    """POST a plain content message to the webhook. files are ignored — we don't ship attachments any more."""
    if os.getenv("DRY_RUN"):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json", "User-Agent": "sinclair-x-bot"},
                                 method="POST")
    try:
        urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:
        print(f"webhook err: {e}", file=sys.stderr)


def main():
    drafts = json.loads(DRAFTS.read_text()) if DRAFTS.exists() else []
    kept = []
    dropped = []
    for d in drafts:
        d["reply"] = humanize(d["reply"])
        why = lint(d["reply"])
        if why:
            dropped.append((d.get("author", "?"), ", ".join(why)))
        else:
            kept.append(d)
    if not kept:
        send({"content": f"ℹ️ No replies to queue ({len(dropped)} dropped by lint)."})
        print("No drafts to queue")
        return
    added = kept
    authors = ", ".join(f"@{d['author']}" for d in added)
    if os.getenv("DRY_RUN"):
        msg = f"[DRY] would queue **{len(added)}** repl{'ies' if len(added) != 1 else 'y'}: {authors}"
        send({"content": msg})
        print(msg)
        return
    from reply_queue import enqueue
    count = enqueue(kept)
    msg = f"Queued {count} new replies with random 30–60 minute gaps: {authors}"
    if dropped:
        msg += f". Dropped {len(dropped)} by lint."
    send({"content": msg})
    print(msg)



if __name__ == "__main__":
    main()
