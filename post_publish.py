"""Publish and read back one post package, with durable IDs before verification.

A saved uncertain submission blocks retries. A verification/source-reply failure
can be resumed without publishing the main post again. No automatic delete/repost.
"""
import fcntl
from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import post_contract as contract
import x_actions as x


def get_tweet(tid):
    url = x.API + '/tweets?' + urllib.parse.urlencode({'tweet_ids': tid})
    request = urllib.request.Request(url, headers={'X-API-Key': x.need('TWITTERAPI_KEY')})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    data = data.get('data', data)
    return next((t for t in data.get('tweets', []) if str(t.get('id')) == str(tid)), None)


def verify_tweet(tweet, text, quote_url=None, image_count=0, parent=None):
    if not tweet:
        raise ValueError('Published tweet is not readable yet')
    if tweet.get('author', {}).get('userName', '').lower() != x.need('X_BOT_USERNAME').lower():
        raise ValueError('Published account does not match configured account')
    actual_quote = (tweet.get('quoted_tweet') or {}).get('id')
    expected_quote = contract.tweet_ref(quote_url)[1] if quote_url else None
    inline_quotes = set()
    for url in re.findall(r'https://\S+', text):
        try:
            inline_quotes.add(contract.tweet_ref(url)[1])
        except ValueError:
            pass
    if ((expected_quote and str(actual_quote) != expected_quote) or
            (not expected_quote and actual_quote and str(actual_quote) not in inline_quotes)):
        raise ValueError('Published quote tweet does not match the draft')
    media = tweet.get('extendedEntities', {}).get('media', [])
    if len(media) != image_count or any(m.get('type') != 'photo' for m in media):
        raise ValueError('Published image attachments do not match the draft')
    if str(tweet.get('inReplyToId') or '') != str(parent or ''):
        raise ValueError('Published reply is attached to the wrong parent')
    actual_mentions = {m.get('screen_name', '').lower() for m in tweet.get('entities', {}).get('user_mentions', [])}
    if not contract.mentions(text).issubset(actual_mentions):
        raise ValueError('Published post is missing an actual @mention')
    actual = tweet.get('text', '')
    # X can prefix replies with inherited @mentions, outside displayTextRange.
    # Offsets use UTF-16, and must be applied before URL/HTML expansion.
    display_range = tweet.get('displayTextRange') or [0]
    start = display_range[0]
    if parent and isinstance(start, int) and start > 0:
        encoded = actual.encode('utf-16-le')
        prefix = encoded[:start * 2].decode('utf-16-le')
        if not re.fullmatch(r'(?:@[A-Za-z0-9_]{1,15}\s+)+', prefix):
            raise ValueError('Unexpected hidden reply prefix')
        actual = encoded[start * 2:].decode('utf-16-le')
    actual = html.unescape(actual)
    text = html.unescape(text)
    for item in tweet.get('entities', {}).get('urls', []):
        if item.get('url') and item.get('expanded_url'):
            actual = actual.replace(item['url'], item['expanded_url'])
    # X appends media/quote URLs that are not part of the author's text.
    if not actual.startswith(text):
        raise ValueError('Published text differs from the approved draft')
    suffix = actual[len(text):].strip()
    allowed = {m.get('url') for m in media}
    if quote_url:
        allowed.add(quote_url)
        for item in tweet.get('entities', {}).get('urls', []):
            try:
                if contract.tweet_ref(item.get('expanded_url'))[1] == expected_quote:
                    allowed.add(item['expanded_url'])
            except ValueError:
                pass
    if any(token not in allowed for token in suffix.split()):
        raise ValueError('Published post has unexpected extra text')


def read_and_verify(tid, **expected):
    last_error = None
    for attempt in range(3):
        try:
            tweet = get_tweet(tid)
            verify_tweet(tweet, **expected)
            return
        except (OSError, ValueError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(2)
    raise RuntimeError(f'Post {tid} exists; verification failed: {last_error}. Do not repost.')


def publish_post(post, root):
    contract.validate_post(post, root)
    x.load_env()
    day = datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()
    identity = {'day': day, 'account': x.need('X_BOT_USERNAME').lower(), 'post': post}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = Path(root) / 'out' / 'publications'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{key}.json'
    with (folder / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        active_path = folder / 'active.json'
        if active_path.exists():
            active = json.loads(active_path.read_text())
            if active['key'] != key:
                previous = json.loads((folder / f"{active['key']}.json").read_text())
                if not previous.get('complete'):
                    raise RuntimeError('An earlier publication is incomplete; inspect its receipt before replacing the draft')
        receipt = json.loads(path.read_text()) if path.exists() else {}

        def save():
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(receipt, indent=2) + '\n')
            temporary.replace(path)

        # Establish the receipt before the first external write, including uploads.
        save()
        active_tmp = active_path.with_suffix('.tmp')
        active_tmp.write_text(json.dumps({'key': key, 'day': day}))
        active_tmp.replace(active_path)

        def submit(label, body):
            if receipt.get(label + '_id'):
                return receipt[label + '_id']
            if receipt.get(label + '_submitting'):
                raise RuntimeError(f'Uncertain {label} submission in {path}; inspect X before retrying')
            receipt[label + '_submitting'] = True
            save()
            result = x.act('create_tweet_v2', body)
            tid = result.get('tweet_id')
            if not tid:
                raise RuntimeError(f'No ID for {label}; inspect X before retrying')
            receipt[label + '_id'] = str(tid)
            receipt[label + '_submitting'] = False
            save()
            return str(tid)

        if not receipt.get('main_id') and not receipt.get('main_submitting'):
            images = contract.validate_assets(post, root)
            ids = receipt.setdefault('media_ids', [])
            proofs = {item['path']: item for item in post.get('image_proof', [])}
            for index, image in enumerate(images[len(ids):], start=len(ids)):
                data = (Path(root) / image).read_bytes()
                if hashlib.sha256(data).hexdigest() != proofs[image]['sha256']:
                    raise ValueError('Proof changed while preparing upload')
                frozen = folder / f'{key}-{index}{Path(image).suffix}'
                frozen.write_bytes(data)
                ids.append(x.upload_image(str(frozen)))
                save()
        body = {'tweet_text': post['text']}
        if post.get('quote_tweet_url'):
            body['attachment_url'] = post['quote_tweet_url']
        if receipt.get('media_ids'):
            body['media_ids'] = receipt['media_ids']
        if len(post['text']) > 280:
            body['is_note_tweet'] = True
        tid = submit('main', body)
        read_and_verify(tid, text=post['text'], quote_url=post.get('quote_tweet_url'),
                        image_count=len(contract.images_for(post)))
        receipt['main_verified'] = True
        save()
        if post.get('source_reply'):
            reply_body = {'tweet_text': post['source_reply'], 'reply_to_tweet_id': tid}
            if len(post['source_reply']) > 280:
                reply_body['is_note_tweet'] = True
            rid = submit('sources', reply_body)
            read_and_verify(rid, text=post['source_reply'], parent=tid)
            receipt['sources_verified'] = True
        receipt['complete'] = True
        save()
        return tid
