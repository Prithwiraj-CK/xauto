"""Fetch @MY_HANDLE's recent tweets so the daily post doesn't repeat itself. Writes out/recent_posts.json.

Env: TWITTERAPI_KEY, MY_HANDLE (default SinClair_0000)
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
ME = os.getenv("MY_HANDLE", "SinClair_0000")


def main():
    url = "https://api.twitterapi.io/twitter/user/last_tweets?" + urllib.parse.urlencode({"userName": ME})
    req = urllib.request.Request(url, headers={"X-API-Key": os.environ["TWITTERAPI_KEY"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    data = data.get("data", data)
    tweets = [{"createdAt": t.get("createdAt"), "text": t.get("text"), "likes": t.get("likeCount"),
               "replies": t.get("replyCount"), "views": t.get("viewCount")} for t in data.get("tweets", [])][:20]
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / "recent_posts.json").write_text(json.dumps(tweets, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(tweets)} recent posts -> out/recent_posts.json")


if __name__ == "__main__":
    main()
