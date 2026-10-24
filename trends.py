"""What people are talking about right now: Meteora / DLMM, viral Solana, Polymarket, and the most argued-about
posts (for hot takes). Writes out/trends.json.

  python3 trends.py            -> last 48h
  python3 trends.py 168        -> last 7 days

Budget: stops fetching once the estimated spend reaches TRENDS_BUDGET_USD (default $0.045,
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
BUDGET = min(float(os.getenv("TRENDS_BUDGET_USD", "0.045")), 0.10)
PER_TWEET, PER_REQUEST = 0.00015, 0.00015
SPAM = re.compile(r"giveaway|airdrop|drop (your|ur) (sol|wallet|addy)|send(ing)? you \$?\d|\bdraw\b|winners?\b.*\$|"
                  r"follow \+|like \+ rt|tag a friend|join (my|our)? ?tg|t\.me/|"
                  r"(comment|drop|send me|post|leave) (your |ur )?(\$?sol(ana)? )?wallets?|blessing|random people|"
                  r"for \d+ of you|\$\d+ to (one|\d+) (person|people)|pick a number|who likes this", re.I)

TOPIC = '(meteora OR dlmm OR "lp army" OR #LPArmy OR "damm v2" OR "dlmm pro" OR $MET)'
QUERIES = [  # (label, query, queryType, max pages)
    ("community", f"{TOPIC} lang:en -filter:retweets -from:{ME} min_faves:5", "Top", 3),
    ("official", "(from:MeteoraAG OR from:met_lparmy OR from:MeteoraEco) -filter:replies", "Latest", 2),
    ("solana-meta", '(solana (memecoin OR memecoins OR trenches OR meta)) lang:en -filter:retweets min_faves:300', "Top", 1),
    ("solana-viral", '(solana OR $SOL OR "solana defi") -giveaway -airdrop -"drop your" lang:en -filter:retweets -filter:replies min_faves:300', "Top", 1),
    ("polymarket", '(polymarket OR "prediction market" OR "prediction markets") lang:en -filter:retweets -filter:replies min_faves:50', "Top", 1),
    ("debates", '(solana OR defi OR memecoin OR kol OR kols OR launchpad OR "crypto twitter") (unpopular OR overrated OR "hot take" OR '
                '"change my mind" OR exposed OR rug OR rugged OR scam OR "wrong about" OR "nobody talks") -giveaway -airdrop '
                'lang:en -filter:retweets -filter:replies min_replies:20', "Top", 1),
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
                if label != "official" and SPAM.search(t.get("text", "")):
                    continue  # giveaways / engagement farms look viral but aren't topics
                rows.append({"author": a.get("userName"), "followers": a.get("followers", 0),
                             "likes": t.get("likeCount", 0), "replies": t.get("replyCount", 0),
                             "reposts": t.get("retweetCount", 0), "quotes": t.get("quoteCount", 0),
                             "views": t.get("viewCount", 0), "created": t.get("createdAt"),
                             "url": t.get("url"), "text": t.get("text", "")})
            if not d.get("has_next_page"):
                break
            cursor = d.get("next_cursor", "")
        seen_text = Counter(re.sub(r"\W+", "", r["text"].lower())[:80] for r in rows)
        rows = [r for r in rows if seen_text[re.sub(r"\W+", "", r["text"].lower())[:80]] == 1]  # copy-paste bait farms
        if label == "debates":  # most arguing: lots of replies relative to likes (and quote-tweets)
            rows.sort(key=lambda t: (t["replies"] + 2 * t["quotes"]) / max(t["likes"], 10), reverse=True)
        else:
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
