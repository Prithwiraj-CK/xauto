"""Find accounts that post about Meteora / DLMM / LP and rank them into a watchlist.

  python3 discover.py          -> out/creators_ranked.json + top 25 printed
  python3 discover.py --apply  -> also writes the top 15 into config/creators.txt (keeps manual entries)

Env: TWITTERAPI_KEY, MY_HANDLE (default SinClair_0000)
Cost: ~10 search pages (~200 tweets) ≈ $0.03 per run.
"""
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
API = "https://api.twitterapi.io/twitter/tweet/advanced_search"
ME = os.getenv("MY_HANDLE", "SinClair_0000").lower()
QUERY = '(meteora OR dlmm OR "lp army" OR #LPArmy OR "damm v2" OR "meteora pool") -filter:retweets lang:en'
SPAM = ("airdrop", "giveaway", "claim now", "presale", "whitelist", "free mint")


def search(query, query_type, pages):
    tweets, cursor = [], ""
    for _ in range(pages):
        url = API + "?" + urllib.parse.urlencode({"query": query, "queryType": query_type, "cursor": cursor})
        req = urllib.request.Request(url, headers={"X-API-Key": os.environ["TWITTERAPI_KEY"]})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        data = data.get("data", data)
        tweets += data.get("tweets", [])
        if not data.get("has_next_page"):
            break
        cursor = data.get("next_cursor", "")
    return tweets


def main():
    tweets = search(QUERY, "Top", 5) + search(QUERY, "Latest", 5)
    authors = defaultdict(lambda: {"posts": 0, "likes": 0, "replies": 0, "followers": 0, "sample": ""})
    seen = set()
    for t in tweets:
        if t["id"] in seen:
            continue
        seen.add(t["id"])
        a = t.get("author", {})
        name = a.get("userName", "")
        text = t.get("text", "")
        if not name or name.lower() == ME or any(w in text.lower() for w in SPAM):
            continue
        d = authors[name]
        d["posts"] += 1
        d["likes"] += t.get("likeCount", 0)
        d["replies"] += t.get("replyCount", 0)
        d["followers"] = max(d["followers"], a.get("followers", 0))
        if len(text) > len(d["sample"]):
            d["sample"] = text[:200]

    ranked = []
    for name, d in authors.items():
        if d["followers"] < 300 or d["followers"] > 1_000_000:  # tiny/bot accounts, and giant generic ones
            continue
        if d["likes"] / d["posts"] < 3:  # posts a lot but nobody engages: repost bots / spam
            continue
        # posting about meteora repeatedly matters most; then engagement; then reach (capped so giants don't dominate)
        d["score"] = round(d["posts"] * 4 + math.log1p(d["likes"] + 3 * d["replies"]) * 2 + min(math.log10(d["followers"]), 5), 2)
        ranked.append({"handle": name, **d})
    ranked.sort(key=lambda x: x["score"], reverse=True)

    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / "creators_ranked.json").write_text(json.dumps(ranked, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(seen)} tweets, {len(ranked)} accounts ranked -> out/creators_ranked.json")
    for r in ranked[:25]:
        print(f"  @{r['handle']:<20} posts {r['posts']:>2}  likes {r['likes']:>5}  followers {r['followers']:>7,}  score {r['score']}")

    if "--apply" in sys.argv:
        path = ROOT / "config" / "creators.txt"
        lines = path.read_text().splitlines() if path.exists() else []
        have = {l.strip().lstrip("@").lower() for l in lines if l.strip() and not l.startswith("#")}
        new = [r["handle"] for r in ranked[:15] if r["handle"].lower() not in have]
        path.write_text("\n".join(lines + new) + "\n")
        print(f"added {len(new)} to config/creators.txt: {', '.join(new)}")


if __name__ == "__main__":
    main()
