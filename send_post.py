"""Auto-post today's draft from out/post.json via x_actions.py.
Legacy name kept so anything invoking `python3 send_post.py` still works.
The webhook now only receives a short ✅ summary with the posted tweet URL; no tap-cards.

post.json: {"type": "...", "text": "...", "quote_tweet_url"?: "...", "images"?: [...], "note"?: "..."}
Env: DISCORD_WEBHOOK_URL (summary only), TWITTERAPI_KEY (via x_actions)
     DRY_RUN=1  -> print what would happen, change nothing
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from send_discord import send

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
    qt_url = post.get("quote_tweet_url") or ""
    images = post.get("images") or ([post["image"]] if post.get("image") else [])
    if not qt_url and not images:
        send({"content": "⚠️ post.json has no proof (quote_tweet_url OR images required) — refusing to post."})
        return
    if qt_url and images:
        send({"content": "⚠️ post.json has both quote_tweet_url AND images — pick one. Refusing to post."})
        return
    for img in images:
        if not (ROOT / img).exists():
            send({"content": f"⚠️ proof image missing: `{img}` — refusing to post."})
            return

    if os.getenv("DRY_RUN"):
        preview = f"QT {qt_url}" if qt_url else f"images: {images}"
        print(f"[DRY] would post ({len(text)} chars, {preview}):\n{text}")
        return

    if qt_url:
        cmd = [sys.executable, "x_actions.py", "qt", qt_url, text]
    else:
        cmd = [sys.executable, "x_actions.py", "tweet", text, *images]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = r.stdout.strip()
    if r.returncode != 0 or "post tweet success" not in out:
        send({"content": f"❌ Post failed:\n```{(r.stderr or out)[:1500]}```"})
        raise SystemExit(1)
    m = re.search(r"'tweet_id': '(\d+)'", out)
    tid = m.group(1) if m else None
    url = f"https://x.com/{os.environ.get('X_BOT_USERNAME','SinClair_0000')}/status/{tid}" if tid else "(no id)"
    kind = post.get("type", "post")
    note = f"\n*note:* {post['note']}" if post.get("note") else ""
    send({"content": f"✅ **Posted** · {kind} ({len(text)} chars)\n{url}{note}"})
    print(f"posted: {url}")


if __name__ == "__main__":
    main()
