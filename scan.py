"""Find fresh Meteora/LP tweets worth replying to. Writes out/candidates.json.

Env: TWITTERAPI_KEY (optional: in the cloud the network proxy injects it)   (twitterapi.io)
     MY_HANDLE        default SinClair_0000 (excluded from results)
     RUN_SLOTS_UTC    run times as decimal UTC hours, default "7.5,9.5,14.5,17.5" (1, 3, 8, 11 PM IST).
                      Each run looks back to the previous slot, so no tweet is seen twice.
     MOCK=1           use tests/mock_search.json instead of calling the API
"""
import json
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent


def twitterapi_headers():
    """Locally the key comes from .env; in the cloud a network secret adds X-API-Key on the way out."""
    key = os.getenv("TWITTERAPI_KEY")
    return {"X-API-Key": key} if key else {}


OUT = ROOT / "out" / "candidates.json"
CREATORS = ROOT / "config" / "creators.txt"
API = "https://api.twitterapi.io/twitter/tweet/advanced_search"

ME = os.getenv("MY_HANDLE", "SinClair_0000")
SLOTS = sorted(float(x) for x in os.getenv("RUN_SLOTS_UTC", "7.5,9.5,14.5,17.5").split(","))
MAX_PAGES = 3  # ~20 tweets/page, ~$0.003/page
MAX_CANDIDATES = 20  # enough to draft 10 after skipping junk
CREATORS_PER_QUERY = 11

KEYWORDS = '(meteora OR dlmm OR "lp army" OR #LPArmy OR "damm v2" OR "meteora pool")'
BASE_FILTERS = f"-filter:replies -filter:retweets -from:{ME}"


def load_creators():
    if not CREATORS.exists():
        return []
    lines = (l.strip().lstrip("@") for l in CREATORS.read_text().splitlines())
    return [l for l in lines if l and not l.startswith("#")]


def search(query):
    if os.getenv("MOCK"):
        return json.loads((ROOT / "tests" / "mock_search.json").read_text())["tweets"]
    tweets, cursor = [], ""
    for _ in range(MAX_PAGES):
        url = API + "?" + urllib.parse.urlencode(
            {"query": query, "queryType": "Latest", "cursor": cursor}
        )
        req = urllib.request.Request(url, headers=twitterapi_headers())
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        data = data.get("data", data)
        tweets += data.get("tweets", [])
        if not data.get("has_next_page"):
            break
        cursor = data.get("next_cursor", "")
    return tweets


def created_at(t):
    return datetime.strptime(t["createdAt"], "%a %b %d %H:%M:%S %z %Y")


def score(t):
    followers = t.get("author", {}).get("followers", 0)
    engagement = t.get("likeCount", 0) + 3 * t.get("replyCount", 0) + t.get("viewCount", 0) / 200
    # Mid-size accounts are the sweet spot: big enough to be seen, small enough to notice you.
    size = math.log10(max(followers, 10))
    if followers > 300_000:
        size -= 1
    return engagement + 5 * size


def window_hours():
    """Hours since the slot before this run's slot (runs can start a few minutes late)."""
    now = datetime.now(timezone.utc)
    h = now.hour + now.minute / 60
    slots = [s - 24 for s in SLOTS] + SLOTS
    current = max(s for s in slots if s <= h + 0.25)  # tolerate starting up to 15 min early
    prev = max(s for s in slots if s < current)
    return h - prev


def main():
    since = int(time.time() - window_hours() * 3600)
    window = f"since_time:{since}"
    queries = [f"{KEYWORDS} {BASE_FILTERS} lang:en {window}"]
    creators = load_creators()
    for i in range(0, len(creators), CREATORS_PER_QUERY):  # keep each search query a sane length
        from_any = " OR ".join(f"from:{c}" for c in creators[i : i + CREATORS_PER_QUERY])
        queries.append(f"({from_any}) {BASE_FILTERS} {window}")

    seen, picked = set(), []
    per_author = {}
    for q in queries:
        for t in search(q):
            if t["id"] in seen or t.get("isReply"):
                continue
            seen.add(t["id"])
            if not os.getenv("MOCK") and created_at(t).timestamp() < since:
                continue
            author = t.get("author", {}).get("userName", "")
            if author.lower() == ME.lower() or per_author.get(author):
                continue
            per_author[author] = True
            picked.append(t)

    picked.sort(key=score, reverse=True)
    out = [
        {
            "id": t["id"],
            "url": t.get("url") or f"https://x.com/{t['author']['userName']}/status/{t['id']}",
            "author": t["author"]["userName"],
            "followers": t["author"].get("followers", 0),
            "likes": t.get("likeCount", 0),
            "replies": t.get("replyCount", 0),
            "views": t.get("viewCount", 0),
            "text": t["text"],
        }
        for t in picked[:MAX_CANDIDATES]
    ]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(out)} candidates from {len(seen)} tweets -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
