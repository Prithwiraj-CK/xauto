"""What people are talking about around Meteora / DLMM right now. Writes out/trends.json.

  python3 trends.py            -> last 48h
  python3 trends.py 168        -> last 7 days

Budget: stops fetching once the estimated spend reaches TRENDS_BUDGET_USD (default $0.03,
never more than $0.10). twitterapi.io bills ~$0.15 per 1K tweets plus a small per-request minimum.

Env: TWITTERAPI_KEY (optional: in the cloud the network proxy injects it), MY_HANDLE
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
API = "https://api.twitterapi.io/twitter/tweet/advanced_search"
ME = os.getenv("MY_HANDLE", "SinClair_0000")
BUDGET = min(float(os.getenv("TRENDS_BUDGET_USD", "0.03")), 0.10)
PER_TWEET, PER_REQUEST = 0.00015, 0.00015

TOPIC = '(meteora OR dlmm OR "lp army" OR #LPArmy OR "damm v2" OR "dlmm pro" OR $MET)'
QUERIES = [  # (label, query, queryType, max pages)
    ("community", f"{TOPIC} lang:en -filter:retweets -from:{ME} min_faves:5", "Top", 3),
    ("official", "(from:MeteoraAG OR from:met_lparmy OR from:MeteoraEco) -filter:replies", "Latest", 2),
    ("solana-meta", '(solana (memecoin OR memecoins OR trenches OR meta)) lang:en -filter:retweets min_faves:300', "Top", 1),
]


def headers():
    key = os.getenv("TWITTERAPI_KEY")
    return {"X-API-Key": key} if key else {}


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 48
    since = int(time.time() - hours * 3600)
    spent, out, seen = 0.0, {}, set()
    for label, q, qtype, pages in QUERIES:
        cursor, rows = "", []
        for _ in range(pages):
            if spent + PER_REQUEST + 20 * PER_TWEET > BUDGET:
                print(f"budget ${BUDGET:.2f} reached, stopping")
                break
            url = API + "?" + urllib.parse.urlencode({"query": f"{q} since_time:{since}", "queryType": qtype, "cursor": cursor})
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers()), timeout=30) as r:
                d = json.load(r)
            d = d.get("data", d)
            tweets = d.get("tweets", [])
            spent += PER_REQUEST + len(tweets) * PER_TWEET
            for t in tweets:
                if t["id"] in seen:
                    continue
                seen.add(t["id"])
                a = t.get("author", {})
                rows.append({"author": a.get("userName"), "followers": a.get("followers", 0),
                             "likes": t.get("likeCount", 0), "replies": t.get("replyCount", 0),
                             "reposts": t.get("retweetCount", 0), "quotes": t.get("quoteCount", 0),
                             "views": t.get("viewCount", 0), "created": t.get("createdAt"),
                             "url": t.get("url"), "text": t.get("text", "")})
            if not d.get("has_next_page"):
                break
            cursor = d.get("next_cursor", "")
        rows.sort(key=lambda t: t["likes"] + 3 * t["replies"] + 2 * t["reposts"], reverse=True)
        out[label] = rows
    text = " ".join(t["text"] for rows in out.values() for t in rows)
    out["summary"] = {
        "hours": hours,
        "tickers": Counter(m.upper() for m in re.findall(r"\$([A-Za-z][A-Za-z0-9]{1,9})\b", text)).most_common(15),
        "hashtags": Counter(m.lower() for m in re.findall(r"#(\w{2,30})", text)).most_common(10),
        "est_cost_usd": round(spent, 4),
    }
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / "trends.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"{sum(len(v) for k, v in out.items() if k != 'summary')} tweets over {hours:.0f}h "
          f"(est ${spent:.4f}) -> out/trends.json")


if __name__ == "__main__":
    main()
