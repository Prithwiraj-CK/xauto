"""Live style references: how Meteora creators are posting and replying right now. Writes out/style.json.

  python3 style.py            -> best posts from the watchlist creators (48h) + most-liked replies under the busiest
                                 official Meteora post and the busiest watchlist post
  python3 style.py --replies  -> replies only (for the reply routine)

Used as tone references only (length, openings, slang, what gets likes), never copied.
Budget: stops at STYLE_BUDGET_USD (default $0.02, never more than $0.10).
Env: TWITTERAPI_KEY (optional: in the cloud the network proxy injects it), MY_HANDLE
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
API = "https://api.twitterapi.io/twitter/"
ME = os.getenv("MY_HANDLE", "SinClair_0000")
BUDGET = min(float(os.getenv("STYLE_BUDGET_USD", "0.02")), 0.10)
OFFICIAL = {"meteoraag", "met_lparmy", "meteoraeco", "meteoraidn", "solana", ME.lower()}
SPAM = re.compile(r"airdrop|giveaway|drop (your|ur) (wallet|addy|sol)|dm me|follow back|presale|whitelist|"
                  r"check my|\bca:|100x|1000x|https?://", re.I)
GIVEAWAY = re.compile(r"\bwinners?\b|congrat|\brt\s*(&|and|\+)|tag \d|retweet|pack worth|\$\d+ each", re.I)
TOPIC = '(meteora OR dlmm OR "lp army" OR "damm v2" OR "dlmm pro")'
spent = 0.0


def call(path, **params):
    global spent
    if spent + 0.00015 + 20 * 0.00015 > BUDGET:
        return None
    key = os.getenv("TWITTERAPI_KEY")
    req = urllib.request.Request(API + path + "?" + urllib.parse.urlencode(params), headers={"X-API-Key": key} if key else {})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    tweets = d.get("tweets") or (d.get("data") or {}).get("tweets") or []
    spent += 0.00015 + len(tweets) * 0.00015
    return tweets


def clean(text):
    return re.sub(r"^(@\w+\s*)+", "", re.sub(r"https?://\S+", "", text or "")).strip()


def creators():
    path = ROOT / "config" / "creators.txt"
    lines = (l.strip().lstrip("@") for l in path.read_text().splitlines()) if path.exists() else []
    return [l for l in lines if l and not l.startswith("#") and l.lower() not in OFFICIAL]


def main():
    since = int(time.time() - 48 * 3600)
    out = {"posts": [], "replies": []}
    handles = creators()
    watch_posts = []
    for i in range(0, len(handles), 12):  # the LP creators we follow, in groups of 12 like scan.py
        group = " OR ".join(f"from:{h}" for h in handles[i:i + 12])
        watch_posts += call("tweet/advanced_search", query=f"({group}) -filter:replies -filter:retweets since_time:{since}",
                            queryType="Latest") or []
    if "--replies" not in sys.argv:
        for t in watch_posts:
            a = t.get("author") or {}
            if SPAM.search(t.get("text", "")) or len(clean(t.get("text"))) < 20:
                continue
            out["posts"].append({"author": a.get("userName"), "followers": a.get("followers", 0), "likes": t.get("likeCount", 0),
                                 "replies": t.get("replyCount", 0), "text": clean(t.get("text"))[:600]})
        out["posts"].sort(key=lambda p: p["likes"] / max(p["followers"], 300) ** 0.5, reverse=True)
        out["posts"] = out["posts"][:8]
    official = call("tweet/advanced_search", query=f"(from:MeteoraAG OR from:met_lparmy OR from:MeteoraEco) -filter:replies "
                                                   f"-filter:retweets since_time:{since}", queryType="Latest") or []
    # giveaways draw the most replies, all "congrats ser": never use them as the tone reference
    official, watch_posts = ([t for t in ts if not SPAM.search(t.get("text", "")) and not GIVEAWAY.search(t.get("text", ""))]
                             for ts in (official, watch_posts))
    parents = sorted(official, key=lambda t: -t.get("replyCount", 0))[:1] + sorted(watch_posts, key=lambda t: -t.get("replyCount", 0))[:1]
    for p in parents:
        if p.get("replyCount", 0) < 3:
            continue
        for r in call("tweet/replies", tweetId=p["id"]) or []:
            text = clean(r.get("text"))
            a = r.get("author") or {}
            if not text or SPAM.search(text) or GIVEAWAY.search(text) or a.get("userName", "").lower() == ME.lower():
                continue
            out["replies"].append({"parent_author": (p.get("author") or {}).get("userName"), "parent_text": clean(p.get("text"))[:200],
                                   "likes": r.get("likeCount", 0), "text": text[:280]})
    out["replies"] = sorted(out["replies"], key=lambda r: -r["likes"])[:15]
    out["est_cost_usd"] = round(spent, 4)
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / "style.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(out['posts'])} creator posts, {len(out['replies'])} replies (est ${spent:.4f}) -> out/style.json")


if __name__ == "__main__":
    main()
