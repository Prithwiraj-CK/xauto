"""Find fresh Meteora/LP tweets worth replying to. Writes out/candidates.json.

Env: TWITTERAPI_KEY   (twitterapi.io)
     MY_HANDLE        default SinClair_0000 (excluded from results)
     WINDOW_HOURS     default 6 (matches 4 runs/day, so no tweet is seen twice)
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
OUT = ROOT / "out" / "candidates.json"
CREATORS = ROOT / "config" / "creators.txt"
API = "https://api.twitterapi.io/twitter/tweet/advanced_search"

ME = os.getenv("MY_HANDLE", "SinClair_0000")
WINDOW_HOURS = float(os.getenv("WINDOW_HOURS", "6"))
MAX_PAGES = 2  # ~20 tweets/page, ~$0.003/page
MAX_CANDIDATES = 8

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
        req = urllib.request.Request(url, headers={"X-API-Key": os.environ["TWITTERAPI_KEY"]})
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


def main():
    since = int(time.time() - WINDOW_HOURS * 3600)
    window = f"since_time:{since}"
    queries = [f"{KEYWORDS} {BASE_FILTERS} lang:en {window}"]
    creators = load_creators()
    if creators:
        from_any = " OR ".join(f"from:{c}" for c in creators)
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
