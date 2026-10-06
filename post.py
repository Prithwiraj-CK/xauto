"""Post the next tweet from content/queue.json. Run once a day.

Env: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
     DRY_RUN=1  -> print instead of posting
     CHECK=1    -> only validate tweet lengths in the queue
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
QUEUE = ROOT / "content" / "queue.json"
STATE = ROOT / "content" / "state.json"
MAX_LEN = 280


def x_length(text: str) -> int:
    """X's weighted length: most Latin chars count 1, everything else (emoji, arrows, CJK) counts 2."""
    one = [(0, 4351), (8192, 8205), (8208, 8223), (8242, 8247)]
    return sum(1 if any(a <= ord(c) <= b for a, b in one) else 2 for c in text)


def check(queue):
    bad = 0
    for i, item in enumerate(queue):
        n = x_length(item["text"])
        flag = "TOO LONG" if n > MAX_LEN else "ok"
        bad += n > MAX_LEN
        print(f"{i:>2} {item['pillar']:<9} {n:>3}  {flag}")
    return bad


def main():
    queue = json.loads(QUEUE.read_text())

    if os.getenv("CHECK"):
        sys.exit(1 if check(queue) else 0)

    state = json.loads(STATE.read_text())
    i = state["next_index"]
    if i >= len(queue):
        print("Queue empty: add more tweets to content/queue.json")
        sys.exit(1)

    text = queue[i]["text"]
    if x_length(text) > MAX_LEN:
        print(f"Tweet {i} is over {MAX_LEN} chars, fix it first")
        sys.exit(1)

    if os.getenv("DRY_RUN"):
        print(f"[dry run] tweet {i}:\n{text}")
        return

    import tweepy

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
    )
    resp = client.create_tweet(text=text)
    tweet_id = resp.data["id"]
    print(f"Posted tweet {i}: https://x.com/i/status/{tweet_id}")

    state["next_index"] = i + 1
    state["posted"].append(
        {"index": i, "id": tweet_id, "at": datetime.now(timezone.utc).isoformat()}
    )
    STATE.write_text(json.dumps(state, indent=2) + "\n")


if __name__ == "__main__":
    main()
