"""Codex daily post and independent reply sessions. Called by local launchd jobs."""
import argparse
from collections import Counter
from datetime import datetime, timedelta
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

import run_daily as rules
import reply_queue

ROOT = Path(__file__).parent
IST = ZoneInfo('Asia/Kolkata')
SLOTS = ['solana-viral', 'hot-take', 'meteora', 'solana-viral', 'polymarket', 'hot-take', 'journey']
REPLY_HOURS = (13, 15, 20, 23)


def now_ist():
    return datetime.now(IST)


def session(mode, now):
    if mode == 'daily':
        # Do not publish yesterday's missed evening post on a morning wake.
        return 'daily' if (now.hour, now.minute) >= (21, 31) else None
    hours = [hour for hour in REPLY_HOURS if hour <= now.hour]
    return f'replies-{max(hours):02d}' if hours else None


def read_json(path):
    return json.loads(path.read_text())


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.replace(path)


def checked(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, check=True, **kw)


def validate_post(post, day):
    text = post.get('text', '')
    if not isinstance(text, str) or not text.strip() or len(text) > 700 or rules.lint_post(text):
        raise ValueError('Post is empty, too long, or failed voice checks')
    if re.search(r'\[[^\]]+\]', text):
        raise ValueError('Post contains an unfilled placeholder')
    expected = SLOTS[datetime.fromisoformat(day).weekday()]
    if post.get('type') != expected:
        # PLAN.md allows a documented breaking-news override, never silent topic drift.
        override = post.get('schedule_override', {})
        if (post.get('type') not in SLOTS or not override.get('reason') or
                not re.fullmatch(r'https://\S+', override.get('source_url', ''))):
            raise ValueError(f'Expected {expected}; breaking-news overrides require a reason and source URL')
        previous_day = (datetime.fromisoformat(day) - timedelta(days=1)).date().isoformat()
        if rules.read_state().get(previous_day, {}).get('post_type') == post['type']:
            raise ValueError('Breaking-news override repeats yesterday’s topic type')
    qt, images = post.get('quote_tweet_url'), post.get('images') or []
    if qt and images:
        raise ValueError('Choose quote tweet or image proof')
    if post['type'] in rules.POST_TYPES_REQUIRING_PROOF and not (qt or images):
        raise ValueError('This topic requires proof')
    if qt and not re.fullmatch(r'https://(?:www\.)?(?:x|twitter)\.com/[^/]+/status/\d+(?:\?[^\s]*)?', qt):
        raise ValueError('Invalid source tweet URL')
    if any(not (ROOT / image).is_file() for image in images):
        raise ValueError('Missing proof image')


def validate_replies(drafts, cap, candidates):
    if not isinstance(drafts, list) or len(drafts) > cap:
        raise ValueError(f'Reply cap is {cap}')
    sources = {str(item['id']): item for item in candidates}
    seen = set()
    words = Counter()
    for draft in drafts:
        tid = str(draft.get('id', ''))
        reply = draft.get('reply', '')
        source = sources.get(tid)
        if not tid.isdigit() or tid in seen or not source:
            raise ValueError('Reply source is missing, duplicated, or absent from this scan')
        if draft.get('author') != source['author'] or draft.get('text') != source['text']:
            raise ValueError('Reply source does not match the scan')
        if not isinstance(reply, str) or not reply.strip() or rules.lint_reply(reply):
            raise ValueError('Reply failed voice checks')
        seen.add(tid)
        words.update(re.findall(r'\b(?:lol|honestly|ngl|tbh)\b', reply.lower()))
    if any(count > 1 for count in words.values()):
        raise ValueError('Repeated crutch words across replies')


def generate(prompt_file, output, context):
    output.unlink(missing_ok=True)
    prompt = (ROOT / prompt_file).read_text() + '\n\n' + context + f'\nWrite your final JSON to {output.relative_to(ROOT)}.\n'
    checked(['/opt/homebrew/bin/codex', '--approve-for-me', '-C', str(ROOT), '--search', 'exec', '-'],
            input=prompt, text=True, timeout=2700)
    return read_json(output)


def push_draft(day):
    # Publishing is complete before this backup step; push failures cannot trigger a second post.
    checked(['git', 'add', 'out/post.json', 'out/draft_state.json'])
    diff = subprocess.run(['git', 'diff', '--cached', '--quiet', '--', 'out/post.json', 'out/draft_state.json'], cwd=ROOT)
    if diff.returncode == 1:
        checked(['git', '-c', 'user.name=Prithwiraj CK', '-c', 'user.email=prithwirajck2@gmail.com',
                 'commit', '--only', '-m', f'Codex daily post for {day}', '--', 'out/post.json', 'out/draft_state.json'])
    elif diff.returncode:
        raise RuntimeError('Could not inspect draft changes')
    checked(['git', 'push', 'origin', 'main'])


def daily(day, folder):
    state = rules.read_state().get(day, {})
    if state.get('post_tweet_id'):
        print(f'Already posted for {day}', flush=True)
        if not (folder / 'backed_up.json').exists() and rules.codex_draft_valid(day, include_replies=False):
            push_draft(day)
            save_json(folder / 'backed_up.json', {'done': True})
        return
    if not rules.codex_draft_valid(day, include_replies=False):
        output = folder / 'post.json'
        post = generate('CODEX_DRAFT.md', output, f'Target date: {day} (IST), TODAY. Required weekday topic: {SLOTS[datetime.fromisoformat(day).weekday()]}.')
        validate_post(post, day)
        if now_ist().date().isoformat() != day:
            raise ValueError('Draft finished after midnight; refusing to publish under the wrong day')
        save_json(ROOT / 'out/post.json', post)
        save_json(ROOT / 'out/draft_state.json', {
            'drafted_for': day, 'at': now_ist().isoformat(), 'generator': 'codex',
            'post_sha256': hashlib.sha256((ROOT / 'out/post.json').read_bytes()).hexdigest(),
        })
    validate_post(read_json(ROOT / 'out/post.json'), day)
    checked([sys.executable, 'run_daily.py', '--post-only'])
    push_draft(day)
    save_json(folder / 'backed_up.json', {'done': True})


def replies(day, slot, folder):
    stamp = folder / 'queued.json'
    if stamp.exists():
        print(f'Already queued {day} {slot}', flush=True)
        return
    cap = 10 if slot == 'replies-13' else 3
    output = folder / 'replies.json'
    sources = folder / 'candidates.json'
    ready = folder / 'validated.json'
    if not ready.exists():
        # Scan must succeed; do not fall back to old candidates from a failed scan.
        checked([sys.executable, 'scan.py'])
        save_json(sources, read_json(ROOT / 'out/candidates.json'))
        drafts = generate('CODEX_REPLIES.md', output,
                          f'Target session: {day} {slot} IST. Maximum replies: {cap}. Use sources in {sources.relative_to(ROOT)}.')
        validate_replies(drafts, cap, read_json(sources))
        save_json(ready, {'sha256': hashlib.sha256(output.read_bytes()).hexdigest()})
    if read_json(ready)['sha256'] != hashlib.sha256(output.read_bytes()).hexdigest():
        raise ValueError('Reply batch changed after validation')
    drafts = read_json(output)
    validate_replies(drafts, cap, read_json(sources))
    added = reply_queue.enqueue(drafts)
    save_json(stamp, {'at': now_ist().isoformat(), 'added': added, 'total': len(drafts)})
    rules.webhook(f'Codex {slot} ({day}): {len(drafts)} replies drafted, {added} added to the queue. Random 30–60 minute gaps.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['daily', 'replies'])
    args = parser.parse_args()
    rules.load_env()
    (ROOT / 'out').mkdir(exist_ok=True)
    # Serialize research and shared files across the independent launchd jobs.
    with (ROOT / 'out' / '.codex-schedule.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        now = now_ist()
        slot = session(args.mode, now)
        if not slot:
            print('Outside scheduled hours; waiting for the next session', flush=True)
            return
        day = now.date().isoformat()
        folder = ROOT / 'out/scheduled' / day / slot
        folder.mkdir(parents=True, exist_ok=True)
        print(f'{now.isoformat()} starting {slot}', flush=True)
        try:
            if args.mode == 'daily':
                daily(day, folder)
            else:
                replies(day, slot, folder)
        except Exception as exc:
            rules.webhook(f'Codex {slot} failed: {type(exc).__name__}. See out/codex_draft.log or out/codex_replies.log.')
            raise


if __name__ == '__main__':
    main()
