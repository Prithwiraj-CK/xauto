"""Send drafted replies from out/drafts.json to Discord, each with a one-click "Reply on X" link.

Env: DISCORD_WEBHOOK_URL
     DRY_RUN=1  -> print the payload instead of sending

drafts.json: [{"id", "url", "author", "text", "reply", "why"?}, ...]
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
DRAFTS = ROOT / "out" / "drafts.json"


def intent_url(tweet_id, reply):
    return "https://x.com/intent/post?" + urllib.parse.urlencode(
        {"in_reply_to": tweet_id, "text": reply}, quote_via=urllib.parse.quote
    )


def embed(d):
    tweet = d["text"] if len(d["text"]) <= 700 else d["text"][:700] + "…"
    parts = [
        f"> {tweet.replace(chr(10), chr(10) + '> ')}",
        f"**Draft reply:**\n{d['reply']}",
    ]
    if d.get("why"):
        parts.append(f"*{d['why']}*")
    parts.append(
        f"**[✍️ Reply]({intent_url(d['id'], d['reply'])})** · [open tweet]({d['url']})"
    )
    return {
        "title": f"@{d['author']}",
        "url": d["url"],
        "description": "\n\n".join(parts)[:4000],
        "color": 0xF5A623,
    }


def send(payload, files=()):
    """POST to the webhook. `files` are local paths sent as attachments (multipart)."""
    if os.getenv("DRY_RUN"):
        print(json.dumps(payload, indent=2, ensure_ascii=False), *(f"[attach {f}]" for f in files))
        return
    if files:
        boundary = "sinclairxbotboundary"
        parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\n'
                 f"Content-Type: application/json\r\n\r\n{json.dumps(payload)}\r\n".encode()]
        for i, f in enumerate(files):
            f = Path(f)
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="files[{i}]"; filename="{f.name}"\r\n'
                         f"Content-Type: image/png\r\n\r\n".encode() + f.read_bytes() + b"\r\n")
        data = b"".join(parts) + f"--{boundary}--\r\n".encode()
        ctype = f"multipart/form-data; boundary={boundary}"
    else:
        data, ctype = json.dumps(payload).encode(), "application/json"
    req = urllib.request.Request(
        os.environ["DISCORD_WEBHOOK_URL"],
        data=data,
        headers={"Content-Type": ctype, "User-Agent": "sinclair-x-bot"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=60).read()


def main():
    drafts = json.loads(DRAFTS.read_text()) if DRAFTS.exists() else []
    if not drafts:
        print("No drafts to send")
        return
    # Discord allows 10 embeds and 6000 embed characters per message
    batches, size = [[]], 0
    for e in map(embed, drafts):
        n = len(e["title"]) + len(e["description"])
        if batches[-1] and (len(batches[-1]) == 10 or size + n > 5800):
            batches.append([])
            size = 0
        batches[-1].append(e)
        size += n
    for i, batch in enumerate(batches):
        content = f"**{len(drafts)} new reply draft{'s' if len(drafts) != 1 else ''}**" if i == 0 else None
        send({"content": content, "embeds": batch})
    print(f"Sent {len(drafts)} drafts to Discord")


if __name__ == "__main__":
    main()
