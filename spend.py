"""Track twitterapi.io spend. 1 USD = 100,000 credits.

  python3 spend.py                         -> print current balance
  python3 spend.py start                   -> remember balance before a run (out/spend_start.json)
  python3 spend.py end <label> <runs/day>  -> cost of this run, balance, monthly estimate -> Discord

Env: TWITTERAPI_KEY, DISCORD_WEBHOOK_URL (for `end`)
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
START = ROOT / "out" / "spend_start.json"
CREDITS_PER_USD = 100_000
LOW_BALANCE_USD = 1.0


def balance_usd():
    req = urllib.request.Request("https://api.twitterapi.io/oapi/my/info",
                                 headers={"X-API-Key": os.environ["TWITTERAPI_KEY"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["recharge_credits"] / CREDITS_PER_USD


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    bal = balance_usd()
    if cmd == "start":
        START.parent.mkdir(exist_ok=True)
        START.write_text(json.dumps({"balance_usd": bal}))
        print(f"balance ${bal:.4f}")
        return
    if cmd != "end":
        print(f"twitterapi.io balance: ${bal:.4f}")
        return

    label = sys.argv[2] if len(sys.argv) > 2 else "run"
    runs_per_day = float(sys.argv[3]) if len(sys.argv) > 3 else 1
    before = json.loads(START.read_text())["balance_usd"] if START.exists() else bal
    cost = max(before - bal, 0)
    monthly = cost * runs_per_day * 30
    days_left = bal / (cost * runs_per_day) if cost else None
    line = (f"💰 twitterapi.io · {label} run cost **${cost:.4f}** · balance **${bal:.2f}** · "
            f"≈ ${monthly:.2f}/month for this job" + (f" · ~{days_left:.0f} days left" if days_left else ""))
    if bal < LOW_BALANCE_USD:
        line += f"\n⚠️ **balance under ${LOW_BALANCE_USD:.0f}: top up at twitterapi.io**"
    print(line)
    from send_discord import send
    send({"content": line})


if __name__ == "__main__":
    main()
