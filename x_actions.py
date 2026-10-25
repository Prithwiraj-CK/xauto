"""Act as a SECONDARY X account through twitterapi.io (login once, then like / reply). Never run this on the main account.

  python3 x_actions.py status                      -> what's configured, cookie age, today's action count
  python3 x_actions.py login                       -> one login ($0.10), saves the cookie to out/x_session.json
  python3 x_actions.py like <tweet_id>             -> $0.0006
  python3 x_actions.py reply <tweet_id> "text"     -> $0.0006

Safety rails: one login only (refuses to log in again while a cookie exists, unless --force), a daily action cap
(X_BOT_DAILY_CAP, default 5) and a minimum gap between actions (X_BOT_MIN_GAP_SEC, default 300). The same proxy is
sent on every call. Stops on the first error from X: check the account by hand before retrying.

Env (.env, gitignored): TWITTERAPI_KEY, X_BOT_USERNAME, X_BOT_EMAIL, X_BOT_PASSWORD, X_BOT_TOTP_SECRET (base32 seed),
X_BOT_PROXY (http://user:pass@ip:port)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
SESSION = ROOT / "out" / "x_session.json"
LOG = ROOT / "out" / "x_actions_log.json"
API = "https://api.twitterapi.io/twitter"


def load_env():
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def need(name):
    v = os.getenv(name)
    if not v:
        sys.exit(f"missing {name} in .env")
    return v


def post(path, body):
    req = urllib.request.Request(f"{API}/{path}", data=json.dumps(body).encode(), method="POST",
                                 headers={"X-API-Key": need("TWITTERAPI_KEY"), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.code}: {e.read().decode()[:300]}"}


def read_json(p, default):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def write_private(p, data):
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    p.chmod(0o600)


def todays_actions():
    log = read_json(LOG, [])
    return [t for t in log if time.time() - t < 86400]


def guard():
    """Daily cap + minimum gap, so a stray loop can't burst."""
    recent = todays_actions()
    if len(recent) >= int(os.getenv("X_BOT_DAILY_CAP", 5)):
        sys.exit(f"daily cap reached ({len(recent)} actions in the last 24h)")
    gap = int(os.getenv("X_BOT_MIN_GAP_SEC", 300))
    if recent and time.time() - max(recent) < gap:
        sys.exit(f"too soon: wait {int(gap - (time.time() - max(recent)))}s since the last action")


def record():
    write_private(LOG, todays_actions() + [time.time()])


def cookies():
    s = read_json(SESSION, {})
    if not s.get("login_cookies"):
        sys.exit("no saved session: run `python3 x_actions.py login` first")
    return s["login_cookies"]


def cmd_login(force):
    if SESSION.exists() and not force:
        sys.exit("a session already exists: reuse it. A second login costs $0.10 and is a new sign-in for X (--force to override)")
    res = post("user_login_v2", {"user_name": need("X_BOT_USERNAME"), "email": need("X_BOT_EMAIL"),
                                 "password": need("X_BOT_PASSWORD"), "totp_secret": need("X_BOT_TOTP_SECRET"),
                                 "proxy": need("X_BOT_PROXY")})
    cookie = res.get("login_cookies") or res.get("login_cookie")
    if res.get("status") != "success" or not cookie:
        sys.exit(f"login failed: {res.get('message') or res}")
    write_private(SESSION, {"login_cookies": cookie, "at": time.time()})
    print("logged in, session saved to out/x_session.json")


def act(path, body):
    guard()
    res = post(path, {**body, "login_cookies": cookies(), "proxy": need("X_BOT_PROXY")})
    if res.get("status") != "success":
        sys.exit(f"stopped, X said: {res.get('message') or res}. Check the account by hand before retrying.")
    record()
    print("ok", {k: v for k, v in res.items() if k != "status"})


def main():
    load_env()
    args = [a for a in sys.argv[1:] if a != "--force"]
    cmd = args[0] if args else ""
    if cmd == "login":
        cmd_login("--force" in sys.argv)
    elif cmd == "like" and len(args) == 2:
        act("like_tweet_v2", {"tweet_id": args[1]})
    elif cmd == "reply" and len(args) == 3:
        act("create_tweet_v2", {"tweet_text": args[2], "reply_to_tweet_id": args[1]})
    elif cmd == "status":
        s = read_json(SESSION, {})
        for k in ("TWITTERAPI_KEY", "X_BOT_USERNAME", "X_BOT_EMAIL", "X_BOT_PASSWORD", "X_BOT_TOTP_SECRET", "X_BOT_PROXY"):
            print(f"{k}: {'set' if os.getenv(k) else 'MISSING'}")
        print("session:", f"saved {(time.time() - s['at']) / 3600:.1f}h ago" if s else "none")
        print(f"actions in last 24h: {len(todays_actions())} / {os.getenv('X_BOT_DAILY_CAP', 5)}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
