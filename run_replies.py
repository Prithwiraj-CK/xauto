"""Drain the shared reply queue with persisted 30–60 minute spacing and one worker."""
import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import reply_queue

ROOT = Path(__file__).parent
LOG = ROOT / 'out' / 'run_replies.log'


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open('a') as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")


def deliver(draft):
    for attempt in range(3):
        p = subprocess.run([sys.executable, str(ROOT / 'x_actions.py'), 'reply',
                            str(draft['id']), draft['reply']],
                           env={**os.environ, 'X_BOT_MIN_GAP_SEC': '10'},
                           capture_output=True, text=True, cwd=str(ROOT))
        combined = (p.stderr + p.stdout).lower()
        if p.returncode == 0 and 'ok' in p.stdout:
            return 'sent'
        if 'already been posted' in combined or 'duplicate' in combined:
            return 'duplicate'
        if any(s in combined for s in ('nodename', 'timed out', 'temporary failure', 'connection reset')) and attempt < 2:
            time.sleep(30)
            continue
        log(f"FAIL @{draft.get('author', '?')}: {combined[:500]}")
        return 'failed'


def main():
    from run_daily import load_env, webhook
    load_env()
    (ROOT / 'out').mkdir(exist_ok=True)
    with (ROOT / 'out' / '.reply-worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        reply_queue.import_legacy()
        sent = 0
        while True:
            row = reply_queue.next_reply()
            if not row:
                if sent:
                    webhook(f'Reply queue finished: {sent} replies posted in this run.')
                return
            wait = row['due'] - time.time()
            if wait > 0:
                time.sleep(min(wait, 60))
                continue
            draft = json.loads(row['payload'])
            status = deliver(draft)
            reply_queue.finish(row['id'], status)
            log(f"{status.upper()} @{draft.get('author', '?')} source={row['id']}")
            if status == 'failed':
                webhook(f"Reply failed for @{draft.get('author', '?')}; saved as failed, see out/run_replies.log. Remaining replies stay queued.")
                return
            sent += status == 'sent'


if __name__ == '__main__':
    main()
