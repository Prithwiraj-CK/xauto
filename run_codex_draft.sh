#!/bin/zsh
set -euo pipefail

repo=/Users/prithiraj/sinclair-x-bot
codex_bin=/opt/homebrew/bin/codex
log="$repo/out/codex_draft.log"
lock="$repo/out/.codex-draft.lock"
mkdir -p "$repo/out"

target=$(/usr/bin/python3 -c 'from datetime import datetime,timedelta; from zoneinfo import ZoneInfo; print((datetime.now(ZoneInfo("Asia/Kolkata"))+timedelta(days=1)).date())')
if /usr/bin/python3 - "$repo/out/draft_state.json" "$target" <<'PY'
import json, sys
try:
    state = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    state = {}
sys.exit(0 if state.get('drafted_for') == sys.argv[2] and not state.get('failed') else 1)
PY
then
    exit 0
fi

if ! mkdir "$lock" 2>/dev/null; then
    exit 0
fi
trap 'rmdir "$lock" 2>/dev/null || true' EXIT

cd "$repo"
{
    echo "[$(/bin/date -u '+%Y-%m-%dT%H:%M:%SZ')] Codex draft for $target"
    git pull --ff-only origin main
    { cat CODEX_DRAFT.md; printf '\nScheduler target date: %s (Asia/Kolkata).\n' "$target"; } | "$codex_bin" --approve-for-me -C "$repo" --search exec -
    /usr/bin/python3 - "$target" <<'PY'
import json, sys
import re
from collections import Counter
from pathlib import Path
from datetime import date
import run_daily as rules
target = sys.argv[1]
state = json.loads(Path('out/draft_state.json').read_text())
post = json.loads(Path('out/post.json').read_text())
replies = json.loads(Path('out/drafts.json').read_text())
if state.get('drafted_for') != target or state.get('failed') or state.get('generator') != 'codex':
    raise SystemExit('Codex did not mark a successful draft for the target date')
if not post.get('text') or len(replies) != 5:
    raise SystemExit('Draft is missing post text or five replies')
slots = ['solana-viral', 'hot-take', 'meteora', 'solana-viral', 'polymarket', 'hot-take', 'journey']
if post.get('type') != slots[date.fromisoformat(target).weekday()]:
    raise SystemExit('Draft has the wrong slot for the target date')
if post['type'] in rules.POST_TYPES_REQUIRING_PROOF and not (post.get('quote_tweet_url') or post.get('images')):
    raise SystemExit('Draft is missing required proof')
if post.get('quote_tweet_url') and post.get('images'):
    raise SystemExit('Draft has both QT and image proof')
if rules.lint_post(post['text']):
    raise SystemExit('Post failed lint')
if any(rules.lint_reply(item.get('reply', '')) or not str(item.get('id', '')).isdigit() for item in replies):
    raise SystemExit('A reply failed lint or lacks a numeric source tweet ID')
words = Counter(word for item in replies for word in re.findall(r"\b(?:lol|honestly|ngl|tbh)\b", item['reply'].lower()))
if any(n > 1 for n in words.values()):
    raise SystemExit('A crutch word appears in multiple replies')
PY
    /usr/bin/python3 run_daily.py --dry
    /usr/bin/python3 - <<'PY'
import hashlib, json
from pathlib import Path
path = Path('out/draft_state.json')
state = json.loads(path.read_text())
state['post_sha256'] = hashlib.sha256(Path('out/post.json').read_bytes()).hexdigest()
state['drafts_sha256'] = hashlib.sha256(Path('out/drafts.json').read_bytes()).hexdigest()
path.write_text(json.dumps(state, indent=2) + '\n')
PY
    git add out/post.json out/drafts.json out/draft_state.json
    git -c user.name='Prithwiraj CK' -c user.email='prithwirajck2@gmail.com' commit -m "Daily Codex draft for $target"
    git push origin main
    /usr/bin/python3 - <<'PY'
import json, urllib.request
from pathlib import Path
env = {}
for line in Path('.env').read_text().splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip('"')
url = env.get('DISCORD_WEBHOOK_URL')
if url:
    post = json.loads(Path('out/post.json').read_text())
    replies = json.loads(Path('out/drafts.json').read_text())
    title = post['text'].splitlines()[0][:140]
    proof = post.get('quote_tweet_url') or ', '.join(post.get('images', [])) or 'pure post'
    authors = ', '.join('@' + x['author'] for x in replies)
    content = f"✅ Codex evening draft done. {post['type']}: {title} ({len(post['text'])} chars). {proof}. Replies: {authors}."
    req = urllib.request.Request(url, json.dumps({'content': content}).encode(), {'Content-Type': 'application/json'})
    urllib.request.urlopen(req, timeout=20).read()
PY
} >> "$log" 2>&1
