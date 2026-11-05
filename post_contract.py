"""Shared pre-publication checks. Provenance records support, not replace, visual review."""
from datetime import datetime, timezone, timedelta
import hashlib
from pathlib import Path
import re
from urllib.parse import urlparse

import post_voice

KINDS = {'opinion', 'reaction', 'research', 'investigation', 'journey'}
PROOF_TOPICS = {'solana-viral', 'meteora', 'polymarket'}
TWEET_URL = re.compile(r'https://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})/status/(\d+)(?:\?[^\s]*)?')
MENTION = re.compile(r'(?<![\w@])@([A-Za-z0-9_]{1,15})(?![\w])')


def tweet_ref(url):
    match = TWEET_URL.fullmatch(url) if isinstance(url, str) else None
    if not match:
        raise ValueError('Invalid source tweet URL')
    return match.group(1).lower(), match.group(2)


def mentions(text):
    return {handle.lower() for handle in MENTION.findall(text)}


def images_for(post):
    if post.get('image'):
        raise ValueError('Use images[] with image_proof records, not legacy image')
    images = post.get('images', [])
    if not isinstance(images, list) or len(images) > 4 or any(not isinstance(p, str) or not p for p in images):
        raise ValueError('images must contain at most four paths')
    if len(images) != len(set(images)):
        raise ValueError('Duplicate proof image')
    return images


def https_url(url):
    if not isinstance(url, str) or re.search(r'\s', url):
        return False
    parsed = urlparse(url)
    return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username


def checked_time(value):
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError()
    except (AttributeError, TypeError, ValueError):
        raise ValueError('Evidence timestamps need a real timezone-aware ISO date') from None


def validate_assets(post, root):
    """Run again immediately before upload so changed screenshots cannot pass an old review."""
    images = images_for(post)
    proofs = post.get('image_proof', [])
    if not isinstance(proofs, list) or any(not isinstance(p, dict) for p in proofs):
        raise ValueError('image_proof must be a list of provenance records')
    if len(proofs) != len(images) or {p.get('path') for p in proofs} != set(images):
        raise ValueError('Every attached image needs exactly one image_proof record')
    for proof in proofs:
        path = Path(root) / proof['path']
        if not path.is_file():
            raise ValueError('Missing proof image')
        data = path.read_bytes()
        is_image = (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff') or
                    (data.startswith(b'RIFF') and data[8:12] == b'WEBP'))
        if not is_image or len(data) > 5 * 1024 * 1024:
            raise ValueError('Proof must be a PNG, JPEG or WebP image under 5 MB')
        if hashlib.sha256(data).hexdigest() != proof.get('sha256'):
            raise ValueError('Proof image changed after review or has no SHA256')
        if proof.get('kind') not in {'screenshot', 'source_image', 'data_chart'}:
            raise ValueError('Use authentic screenshots, original source images or reproducible data charts')
        if not https_url(proof.get('source_url')) or not proof.get('claim') or not proof.get('credit'):
            raise ValueError('Image proof requires its source URL, supported claim and credit')
        checked_time(proof.get('captured_at'))
        if proof.get('visual_review') != {'readable': True, 'authentic': True, 'supports_claim': True}:
            raise ValueError('Inspect each image for readability, authenticity and claim support')
    return images


def validate_post(post, root):
    text = post.get('text')
    if not isinstance(text, str) or not text.strip() or len(text) > 700:
        raise ValueError('Post text is empty or over 700 characters')
    if re.search(r'\[[^\]]+\]', text):
        raise ValueError('Post contains an unfilled placeholder')
    voice_errors = post_voice.lint(text)
    if voice_errors:
        raise ValueError('Editorial rejection: ' + '; '.join(voice_errors))
    kind = post.get('content_kind')
    if kind not in KINDS:
        raise ValueError('Declare content_kind: opinion, reaction, research, investigation or journey')
    targets = post.get('subject_handles', [])
    if not isinstance(targets, list) or any(not isinstance(h, str) or not re.fullmatch(r'[A-Za-z0-9_]{1,15}', h) for h in targets):
        raise ValueError('subject_handles must be verified handles without @')
    if not {h.lower() for h in targets}.issubset(mentions(text)):
        raise ValueError('A named subject is missing its actual @mention in the post')
    if len(mentions(text)) > 2:
        raise ValueError('Use at most two relevant @mentions')
    qt = post.get('quote_tweet_url')
    if qt:
        author, _ = tweet_ref(qt)
        if author != 'sinclair_0000' and author not in mentions(text):
            raise ValueError('Quote-tweet author must have an actual @mention in the main text')
    source = post.get('source_tweet_url')
    if source and (not qt or tweet_ref(source) != tweet_ref(qt)):
        raise ValueError('The reaction must quote the exact source tweet')
    if kind in {'reaction', 'investigation'}:
        if not source or not targets:
            raise ValueError('Reactions and investigations require source_tweet_url and subject_handles')
        if tweet_ref(source)[0] not in {h.lower() for h in targets}:
            raise ValueError('Tag the verified author of the quoted public statement')
    images = validate_assets(post, root)
    if post.get('type') in PROOF_TOPICS and not (qt or images):
        raise ValueError('This topic requires a quote tweet or image proof')
    if kind == 'investigation' and not images:
        raise ValueError('Investigations require authentic image receipts as well as the quote tweet')
    sources = post.get('sources', [])
    if not isinstance(sources, list) or any(not isinstance(s, dict) for s in sources):
        raise ValueError('sources must be a list')
    for item in sources:
        if not https_url(item.get('url')) or not item.get('claim'):
            raise ValueError('Each source needs a public URL and the specific claim it supports')
        checked_time(item.get('checked_at'))
    if (kind in {'reaction', 'research', 'investigation'} or images) and not sources:
        raise ValueError('Factual posts and images require checked sources')
    source_urls = {s['url'] for s in sources}
    if qt and tweet_ref(qt)[0] != 'sinclair_0000' and qt not in source_urls:
        raise ValueError('External quote tweets need a checked source record')
    if source and source not in source_urls:
        raise ValueError('The quoted public statement must be included in checked sources')
    if any(p['source_url'] not in source_urls for p in post.get('image_proof', [])):
        raise ValueError('Image provenance must link to a checked source')
    reply = post.get('source_reply', '')
    if not isinstance(reply, str) or len(reply) > 700:
        raise ValueError('source_reply must be text under 700 characters')
    if re.search(r'\[[^\]]+\]', reply) or len(mentions(reply)) > 2:
        raise ValueError('Source reply contains placeholders or too many mentions')
    if images or kind == 'investigation':
        required = {p['source_url'] for p in post.get('image_proof', [])}
        if not reply.strip() or any(url not in reply for url in required):
            raise ValueError('Attach public image source links in source_reply; note is not published')
    return post
