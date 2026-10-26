"""Daily poster: posts out/post.json + schedules replies from out/drafts.json. Idempotent per day. Runs under cron.

  python3 run_daily.py             -> post the daily draft and queue replies
  python3 run_daily.py --dry       -> show what it would do, change nothing
  python3 run_daily.py --post-only -> just the daily tweet, no replies
  python3 run_daily.py --reply-only-> just queue replies, no daily tweet

Inputs:
  out/post.json      {"type", "text", "images": [...], "note"?}       <-- today's post
  out/drafts.json    [{"id": "<tweet_id>", "author", "text", "reply"}, ...]  <-- replies to send

Guards (hard rules):
  - Lints post text + every reply for AI tells; refuses to post anything that fails
  - Requires at least one proof image on the daily post (hard rule)
  - Skips if today's post already posted (stamp in out/run_daily_state.json)
  - Stops the reply chain on the first X failure, logs which ones didn't post
  - Random 30-60 min gaps between replies, each as its own run

Discord webhook only gets $ spent summaries.
Env: TWITTERAPI_KEY, DISCORD_WEBHOOK_URL, X_BOT_* (loaded from .env automatically)
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
STATE = ROOT / "out" / "run_daily_state.json"
POST = ROOT / "out" / "post.json"
DRAFTS = ROOT / "out" / "drafts.json"
LOG = ROOT / "out" / "run_daily.log"

MAX_REPLY_CHARS = 100

# From content/PLAN.md Sound-human section, mirrors send_discord.AI_TELLS plus post-only tells
POST_AI_TELLS = [
    " — ", "—", ";", "here's ", "the lp version", "in one line", "not just ", " but ",
    "it's worth noting", "game changer", "game-changer", "unlock", "landscape",
    "dive in", "let's ", " nuance ", "ecosystem", "robust ",
]
REPLY_AI_TELLS = [
    "great point", "love this", "this is huge", "here's the thing", "that said", "moreover",
    "worth noting", "not just", "game changer", "game-changer", "couldn't agree more", "spot on",
    "the real alpha", "this is why", "imagine", "a monkey that", "one that", "the kind of",
]


def load_env():
    f = ROOT / ".env"
    if f.exists():
        for l in f.read_text().splitlines():
            if "=" in l and not l.lstrip().startswith("#"):
                k, v = l.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    print(msg)


def read_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except ValueError:
            pass
    return {}


def write_state(s):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2))


def today_utc_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def lint_post(text):
    """Returns a list of reasons the text reads as AI; empty if clean."""
    why = []
    low = text.lower()
    for t in POST_AI_TELLS:
        if t in low:
            why.append(f'"{t.strip()}"')
    # lists of exactly three ("X, Y, Z" or "X, Y and Z")
    if re.search(r"\b\w+,\s*\w+,\s*\w+\s+\b", text):
        why.append("list-of-three")
    # X: Y heading on more than one line
    if sum(1 for l in text.splitlines() if re.match(r"^[A-Za-z ]+:\s*\S", l)) > 1:
        why.append("X: Y headings")
    if "#" in text:
        why.append("hashtag")
    return why


def lint_reply(text):
    """Mirrors send_discord.lint() so cron behavior matches Discord drafts."""
    low, why = text.lower(), []
    if len(text) > MAX_REPLY_CHARS:
        why.append(f"{len(text)} chars (max {MAX_REPLY_CHARS})")
    if any(c in text for c in "—–;"):
        why.append("dash or semicolon")
    if text.count(",") > 1 or re.search(r",[^,]*\band\b", low):
        why.append("list")
    if len(re.findall(r"[.!?]\s+\S", text.strip())) > 1:
        why.append("3+ sentences")
    if "#" in text or "http" in low:
        why.append("hashtag or link")
    why += [f'"{t}"' for t in REPLY_AI_TELLS if t in low]
    if low.startswith("absolutely"):
        why.append('"absolutely"')
    return why


def run(cmd, env=None):
    return subprocess.run(cmd, env=env or os.environ.copy(), capture_output=True, text=True, cwd=str(ROOT))


def spend_start():
    run([sys.executable, "spend.py", "start"])


def spend_end(label):
    r = run([sys.executable, "spend.py", "end", label, "1"])
    log(r.stdout.strip() or r.stderr.strip())


def post_daily(dry):
    if not POST.exists():
        log("no out/post.json: skip daily tweet")
        return None
    p = json.loads(POST.read_text())
    text, images = p.get("text", ""), p.get("images") or ([p["image"]] if p.get("image") else [])
    if not text:
        log("post.json has empty text, skip")
        return None
    if not images:
        log("HARD RULE: post has no proof image, refusing to post")
        return None
    for img in images:
        if not (ROOT / img).exists():
            log(f"HARD RULE: proof image missing: {img}, refusing to post")
            return None
    why = lint_post(text)
    if why:
        log(f"HARD RULE: post lint failed ({', '.join(why)}), refusing to post")
        return None
    log(f"post lint ok ({len(text)} chars, {len(images)} proof image{'s' if len(images)!=1 else ''})")
    if dry:
        log(f"[dry] would post: {text[:120]}...")
        return "DRY"
    r = run([sys.executable, "x_actions.py", "tweet", text, *images])
    log(r.stdout.strip())
    if r.returncode != 0 or "post tweet success" not in r.stdout:
        log(f"daily tweet FAILED: {r.stderr.strip()}")
        return None
    m = re.search(r"'tweet_id': '(\d+)'", r.stdout)
    tid = m.group(1) if m else None
    if tid:
        url = f"https://x.com/{os.environ.get('X_BOT_USERNAME','SinClair_0000')}/status/{tid}"
        # update .env for TG engagement later
        env_path = ROOT / ".env"
        txt = env_path.read_text()
        if "X_BOT_LATEST_TWEET_URL" in txt:
            txt = re.sub(r"^X_BOT_LATEST_TWEET_URL=.*$", f"X_BOT_LATEST_TWEET_URL={url}", txt, flags=re.M)
        else:
            txt += f"\nX_BOT_LATEST_TWEET_URL={url}\n"
        env_path.write_text(txt); env_path.chmod(0o600)
        log(f"posted: {url}")
    return tid


def queue_replies(dry):
    if not DRAFTS.exists():
        log("no out/drafts.json: skip replies")
        return 0
    drafts = json.loads(DRAFTS.read_text())
    cleaned = []
    for d in drafts:
        why = lint_reply(d.get("reply", ""))
        if why:
            log(f"skipped @{d.get('author','?')}: {d.get('reply','')!r} ({', '.join(why)})")
        else:
            cleaned.append(d)
    log(f"{len(cleaned)} replies passed lint (of {len(drafts)})")
    if not cleaned:
        return 0
    if dry:
        for d in cleaned:
            log(f"[dry] would reply @{d['author']}: {d['reply']}")
        return len(cleaned)

    # Launch a persistent background Python that sleeps + posts with random 30-60 min gaps
    scratch = ROOT / "out" / "pending_replies.json"
    scratch.write_text(json.dumps(cleaned, indent=2))
    runner = ROOT / "run_replies.py"
    pid = subprocess.Popen([sys.executable, str(runner)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, start_new_session=True).pid
    log(f"backgrounded {len(cleaned)} replies, pid {pid}")
    return len(cleaned)


def main():
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--post-only", action="store_true")
    ap.add_argument("--reply-only", action="store_true")
    ap.add_argument("--force", action="store_true", help="post even if today's run already stamped")
    args = ap.parse_args()

    log(f"run_daily start (dry={args.dry}, post_only={args.post_only}, reply_only={args.reply_only})")
    state = read_state()
    today = today_utc_str()
    if state.get(today) and not args.force and not args.dry:
        log(f"already ran for {today}: {state[today]}. Use --force to re-run.")
        return

    spend_start()
    done = {}
    if not args.reply_only:
        tid = post_daily(args.dry)
        done["post_tweet_id"] = tid
    if not args.post_only:
        n = queue_replies(args.dry)
        done["replies_queued"] = n

    if not args.dry:
        state[today] = done
        write_state(state)
        spend_end("daily run (tweet only)")

    log(f"run_daily done: {done}")


if __name__ == "__main__":
    main()
