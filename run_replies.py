"""Backgrounded reply poster: reads out/pending_replies.json and posts each with a random 30-60 min gap.
Launched by run_daily.py; also safe to run standalone. Stops on first X failure. Logs to out/run_replies.log.
"""
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
PENDING = ROOT / "out" / "pending_replies.json"
LOG = ROOT / "out" / "run_replies.log"

for l in (ROOT / ".env").read_text().splitlines():
    if "=" in l and not l.lstrip().startswith("#"):
        k, v = l.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")


def main():
    if not PENDING.exists():
        log("no pending_replies.json, nothing to do")
        return
    drafts = json.loads(PENDING.read_text())
    log(f"starting with {len(drafts)} replies queued")
    sent = 0
    for i, d in enumerate(drafts):
        gap_min = random.uniform(30, 60)
        log(f"sleep {gap_min:.1f} min before reply {i+1}/@{d.get('author','?')}")
        time.sleep(gap_min * 60)
        env = {**os.environ, "X_BOT_MIN_GAP_SEC": "10"}
        # Retry transient network errors (DNS, timeout) up to 3 times, 30s apart
        posted, skip_only = False, False
        for attempt in range(3):
            p = subprocess.run([sys.executable, str(ROOT / "x_actions.py"), "reply",
                                str(d["id"]), d["reply"]],
                               env=env, capture_output=True, text=True, cwd=str(ROOT))
            combined = (p.stderr + p.stdout).lower()
            if p.returncode == 0 and "ok" in p.stdout:
                log(f"OK reply {i+1} @{d.get('author','?')}: {p.stdout.strip()}")
                sent += 1
                posted = True
                break
            transient = any(s in combined for s in ("nodename", "timed out", "temporary failure", "connection reset"))
            if transient and attempt < 2:
                log(f"transient on reply {i+1}, retry {attempt+1}/3 in 30s")
                time.sleep(30)
                continue
            # 422 "already posted" / "duplicate" = this one reply is dead, but keep the chain alive
            if "already been posted" in combined or "duplicate" in combined or "422" in combined:
                log(f"SKIP reply {i+1} @{d.get('author','?')}: duplicate text, continuing chain")
                skip_only = True
            else:
                log(f"FAIL reply {i+1} @{d.get('author','?')}: rc={p.returncode} out={p.stdout.strip()} err={p.stderr.strip()}")
            break
        if not posted and not skip_only:
            log(f"stopping, {len(drafts)-i-1} replies NOT posted")
            break

    # Clear the queue so a re-run doesn't re-send what already went
    PENDING.unlink(missing_ok=True)

    # Discord spend summary (only $ info)
    try:
        p = subprocess.run([sys.executable, str(ROOT / "spend.py"), "end", f"{sent} replies batch", "1"],
                           env=os.environ.copy(), capture_output=True, text=True, cwd=str(ROOT))
        log(f"spend: {p.stdout.strip()}")
    except Exception as e:
        log(f"spend err: {e}")
    log("done")


if __name__ == "__main__":
    main()
