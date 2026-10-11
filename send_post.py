"""Send today's post draft (out/post.json) to Discord with its image and a one-tap "Post on X" link.

post.json: {"type": "...", "text": "...", "image": "out/chart.png" | null, "note": "optional note for you"}
Env: DISCORD_WEBHOOK_URL, DRY_RUN=1
"""
import base64
import json
import urllib.parse
from pathlib import Path

from send_discord import buttons, send

ROOT = Path(__file__).parent
MAX_LEN = 700
REDIRECT = "https://prithwiraj-ck.github.io/xauto/x.html"


def x_length(text):
    """X's weighted length: most Latin chars count 1, everything else (emoji, arrows, CJK) counts 2."""
    one = [(0, 4351), (8192, 8205), (8208, 8223), (8242, 8247)]
    return sum(1 if any(a <= ord(c) <= b for a, b in one) else 2 for c in text)


def main():
    post = json.loads((ROOT / "out" / "post.json").read_text())
    text = post["text"]
    n = x_length(text)
    if n > MAX_LEN:
        raise SystemExit(f"post is {n} chars, over {MAX_LEN}: shorten it")

    link = "https://x.com/intent/post?" + urllib.parse.urlencode({"text": text}, quote_via=urllib.parse.quote)
    lines = [text, ""]
    image = post.get("image")
    if image:
        lines.append("🖼️ *save the image below, then attach it in X before posting*")
    if post.get("note"):
        lines.append(f"📝 *{post['note']}*")
    embed = {"description": "\n".join(lines), "color": 0x1D9BF0}
    files = []
    if image:
        files = [ROOT / image]
        embed["image"] = {"url": f"attachment://{Path(image).name}"}
    content = f"**📅 Today's post · {post.get('type', 'post')}** ({n} chars)"
    if len(link) > 512:
        # Long prefilled links get mangled by Discord (%-escapes double-encoded), so send the text as base64url
        # to a tiny page in this repo (GitHub Pages, docs/x.html) that opens X's composer with it. No % anywhere.
        link = REDIRECT + "#" + base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")
    if len(link) <= 512:  # Discord link buttons take URLs up to 512 chars
        send({"content": content, "embeds": [embed], "components": buttons([("🚀 Post on X", link)])}, files)
    else:
        send({"content": content + f"\n**[🚀 Post on X]({link})**", "embeds": [embed]}, files)
    print(f"Sent {post.get('type')} post to Discord")


if __name__ == "__main__":
    main()
