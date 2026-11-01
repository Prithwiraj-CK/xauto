"""Track twitterapi.io spend. 1 USD = 100,000 credits.

  python3 spend.py                         -> print current balance
  python3 spend.py start                   -> remember balance before a run (out/spend_start.json)
  python3 spend.py end <label> <runs/day>  -> cost of this run, balance, monthly estimate -> Discord

Env: TWITTERAPI_KEY (optional: in the cloud the network proxy injects it),
WEBSHARE_API_KEY (optional, for proxy renewal date), DISCORD_WEBHOOK_URL (for `end`)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent

# Load .env so TWITTERAPI_KEY and DISCORD_WEBHOOK_URL are available when run from cron / scripts
_env = ROOT / ".env"
if _env.exists():
    for _l in _env.read_text().splitlines():
        if "=" in _l and not _l.lstrip().startswith("#"):
            _k, _v = _l.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


def twitterapi_headers():
    """Locally the key comes from .env; in the cloud a network secret adds X-API-Key on the way out."""
    key = os.getenv("TWITTERAPI_KEY")
    return {"X-API-Key": key} if key else {}


START = ROOT / "out" / "spend_start.json"
CREDITS_PER_USD = 100_000
LOW_BALANCE_USD = 1.0
WEBSHARE_SUBSCRIPTION = "https://proxy.webshare.io/api/v2/subscription/"


def get_json(url, headers):
    """Retry read-only status requests after transient transport or server errors."""
    for attempt in range(3):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 * (attempt + 1))


def balance_usd():
    d = get_json("https://api.twitterapi.io/oapi/my/info", twitterapi_headers())
    # bonus credits are spent first, so count both or early runs look free
    return (d.get("recharge_credits", 0) + d.get("total_bonus_credits", 0)) / CREDITS_PER_USD


def proxy_status(now=None):
    """Return Webshare's current subscription period; never infer it from proxy login credentials."""
    key = os.getenv("WEBSHARE_API_KEY")
    if not key:
        return "Webshare proxy: period unavailable (set WEBSHARE_API_KEY)"
    try:
        data = get_json(WEBSHARE_SUBSCRIPTION, {"Authorization": f"Token {key}"})
        end = datetime.fromisoformat(data["end_date"].replace("Z", "+00:00"))
        if end.tzinfo is None:
            raise ValueError("subscription end_date has no timezone")
        days = max(0, (end - (now or datetime.now(timezone.utc))).total_seconds() / 86400)
        suffix = "until next renewal" if data.get("renewals_enabled") else "in current period"
        return f"Webshare proxy: {days:.1f} days {suffix} (period ends {end.date().isoformat()})"
    except (KeyError, ValueError, TypeError, urllib.error.URLError, TimeoutError, OSError):
        return "Webshare proxy: period unavailable (subscription check failed)"


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
        print(proxy_status())
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
    line += f"\n{proxy_status()}"
    print(line)
    from send_discord import send
    send({"content": line})


if __name__ == "__main__":
    main()
