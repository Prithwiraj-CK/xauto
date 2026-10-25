"""Send drafted replies from out/drafts.json to Discord, each with a one-click "Reply on X" link.

Env: DISCORD_WEBHOOK_URL
     DRY_RUN=1  -> print the payload instead of sending

drafts.json: [{"id", "url", "author", "text", "reply", "why"?}, ...]
"""
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
DRAFTS = ROOT / "out" / "drafts.json"
MAX_CHARS = 100
# phrases that read as AI (REPLY_GUIDE.md "Never" list plus repeat offenders)
AI_TELLS = ["great point", "love this", "this is huge", "here's the thing", "that said", "moreover",
            "worth noting", "not just", "game changer", "game-changer", "couldn't agree more", "spot on",
            "the real alpha", "this is why", "imagine", "a monkey that", "one that", "the kind of"]


def lint(reply):
    """Reasons this draft reads as AI, empty if it passes. The guide is the real rule; this catches what slips through."""
    low, why = reply.lower(), []
    if len(reply) > MAX_CHARS:
        why.append(f"{len(reply)} chars (max {MAX_CHARS})")
    if any(c in reply for c in "—–;"):
        why.append("dash or semicolon")
    if reply.count(",") > 1 or re.search(r",[^,]*\band\b", low):
        why.append("list")
    if len(re.findall(r"[.!?]\s+\S", reply.strip())) > 1:
        why.append("3+ sentences")
    if "#" in reply or "http" in low:
        why.append("hashtag or link")
    why += [f'"{t}"' for t in AI_TELLS if t in low]
    if low.startswith("absolutely"):
        why.append('"absolutely"')
    return why


def humanize(reply):
    """Lowercase first letter (not acronyms) and drop a trailing period, like phone typing."""
    r = reply.strip().rstrip(".")
    return r[0].lower() + r[1:] if len(r) > 1 and r[0].isupper() and not r[1].isupper() else r


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
    parts.append(f"[open tweet]({d['url']}) · tap **✍️ Reply @{d['author']}** below")
    return {
        "title": f"@{d['author']}",
        "url": d["url"],
        "description": "\n\n".join(parts)[:4000],
        "color": 0xF5A623,
    }


def buttons(links):
    """Link buttons, 5 per row. Discord mangles percent-encoded links inside embeds, but not in buttons."""
    btns = [{"type": 2, "style": 5, "label": label[:80], "url": url} for label, url in links]
    return [{"type": 1, "components": btns[i : i + 5]} for i in range(0, len(btns), 5)]


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
        os.environ["DISCORD_WEBHOOK_URL"] + ("?with_components=true" if payload.get("components") else ""),
        data=data,
        headers={"Content-Type": ctype, "User-Agent": "sinclair-x-bot"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=60).read()


def main():
    drafts = json.loads(DRAFTS.read_text()) if DRAFTS.exists() else []
    kept = []
    for d in drafts:
        d["reply"] = humanize(d["reply"])
        why = lint(d["reply"])
        if why:
            print(f"Dropped @{d['author']}: {d['reply']!r} ({', '.join(why)})")
        else:
            kept.append(d)
    drafts = kept
    if not drafts:
        print("No drafts to send")
        return
    # Discord allows 10 embeds and 6000 embed characters per message
    batches, size = [[]], 0
    for d in drafts:
        n = len(f"@{d['author']}") + len(embed(d)["description"])
        if batches[-1] and (len(batches[-1]) == 10 or size + n > 5800):
            batches.append([])
            size = 0
        batches[-1].append(d)
        size += n
    for i, batch in enumerate(batches):
        content = f"**{len(drafts)} new reply draft{'s' if len(drafts) != 1 else ''}**" if i == 0 else None
        send({"content": content, "embeds": [embed(d) for d in batch],
              "components": buttons((f"✍️ Reply @{d['author']}", intent_url(d["id"], d["reply"])) for d in batch)})
    print(f"Sent {len(drafts)} drafts to Discord")


if __name__ == "__main__":
    main()
