"""Send engage-session drafts from out/engage_drafts.json to Discord with Reply + Like link buttons.

Usage: python3 send_engage.py [session_number]
Env: DISCORD_WEBHOOK_URL, DRY_RUN=1 to print payloads instead of sending
"""
import json
import sys
from pathlib import Path

from send_discord import buttons, embed, intent_url, send

DRAFTS = Path(__file__).parent / "out" / "engage_drafts.json"
TWEET_CHARS = 250  # keep ten embeds under Discord's ~6000 char message limit


def main():
    session = sys.argv[1] if len(sys.argv) > 1 else "3"
    drafts = json.loads(DRAFTS.read_text())
    batches = [drafts[i : i + 10] for i in range(0, len(drafts), 10)]
    for i, batch in enumerate(batches):
        embeds = []
        for d in batch:
            e = embed({**d, "text": d["text"][:TWEET_CHARS] + ("…" if len(d["text"]) > TWEET_CHARS else "")})
            e["description"] = e["description"].replace("below", "and **❤️ Like** below")
            embeds.append(e)
        links = []
        for d in batch:
            links.append((f"✍️ Reply @{d['author']}", intent_url(d["id"], d["reply"])))
            links.append((f"❤️ Like @{d['author']}", f"https://x.com/intent/like?tweet_id={d['id']}"))
        content = None
        if i == 0:
            content = (f"**Engage session {session}: {len(drafts)} drafts, reply + like**\n"
                       "Likes and replies must be done by 15:00 UTC.")
        payload = {"content": content, "embeds": embeds, "components": buttons(links)}
        size = sum(len(e["title"]) + len(e["description"]) for e in embeds)
        assert size <= 5800, f"batch {i} embed chars {size}"
        send(payload)
    print(f"Sent {len(drafts)} drafts in {len(batches)} messages")


if __name__ == "__main__":
    main()
