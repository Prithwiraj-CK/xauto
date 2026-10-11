"""Send today's post draft (out/post.json) to Discord with its image and a one-tap "Post on X" link.

post.json: {"type": "...", "text": "...", "image": "out/chart.png" | null, "note": "optional note for you"}
Env: DISCORD_WEBHOOK_URL, DRY_RUN=1
"""
import json
import urllib.parse
from pathlib import Path

from send_discord import buttons, send

ROOT = Path(__file__).parent
MAX_LEN = 1000  # the account has Premium; X allows long posts, but keep most short


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
    content = f"**📅 Today's post · {post.get('type', 'post')}** ({n} chars{', long post' if n > 280 else ''})"
    # Discord link buttons take URLs up to 512 chars. Longer prefilled links go in the message text
    # (links inside embeds get double-encoded by Discord); past Discord's 2000-char limit, open a blank composer.
    if len(link) <= 512:
        components = buttons([("🚀 Post on X", link)])
    elif len(content) + len(link) + 30 <= 2000:
        content += f"\n**[🚀 Post on X]({link})**"
        components = []
    else:
        embed["description"] += "\n\n📋 *too long for a prefilled link: copy the text above, then paste it in X*"
        components = buttons([("🚀 Open X composer", "https://x.com/compose/post")])
    send({"content": content, "embeds": [embed], "components": components}, files)
    print(f"Sent {post.get('type')} post to Discord")


if __name__ == "__main__":
    main()
