"""Auto-post today's draft from out/post.json via x_actions.py.
Legacy name kept so anything invoking `python3 send_post.py` still works.
The webhook now only receives a short ✅ summary with the posted tweet URL; no tap-cards.

post.json: {"type": "...", "text": "...", "quote_tweet_url"?: "...", "images"?: [...], "note"?: "..."}
Env: DISCORD_WEBHOOK_URL (summary only), TWITTERAPI_KEY (via x_actions)
     DRY_RUN=1  -> print what would happen, change nothing
"""
import json
import os
from pathlib import Path

from send_discord import send
from post_contract import validate_post
from post_publish import publish_post
from run_daily import lint_post

ROOT = Path(__file__).parent


def main():
    post_path = ROOT / "out" / "post.json"
    if not post_path.exists():
        send({"content": "⚠️ No out/post.json — nothing to post."})
        return
    post = json.loads(post_path.read_text())
    text = post.get("text", "").strip()
    if not text:
        send({"content": "⚠️ post.json has empty text — refusing to post."})
        return
    validate_post(post, ROOT)
    if lint_post(text):
        raise ValueError('Post failed voice checks')

    if os.getenv("DRY_RUN"):
        preview = f"QT {post.get('quote_tweet_url')}, images: {post.get('images', [])}"
        print(f"[DRY] would post ({len(text)} chars, {preview}):\n{text}")
        return

    tid = publish_post(post, ROOT)
    url = f"https://x.com/{os.environ.get('X_BOT_USERNAME','SinClair_0000')}/status/{tid}" if tid else "(no id)"
    kind = post.get("type", "post")
    note = f"\n*note:* {post['note']}" if post.get("note") else ""
    send({"content": f"✅ **Posted** · {kind} ({len(text)} chars)\n{url}{note}"})
    print(f"posted: {url}")


if __name__ == "__main__":
    main()
