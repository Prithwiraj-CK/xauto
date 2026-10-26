"""Save and swap the X_BOT_* profile in .env + out/x_session.json so Billi and Sinclair can coexist.

  python3 x_profile.py save <name>     -> snapshot current .env X_BOT_* lines and cookie to out/profiles/<name>/
  python3 x_profile.py use  <name>     -> load that snapshot back into .env and out/x_session.json
  python3 x_profile.py list            -> list saved profiles
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
ENV = ROOT / ".env"
SESSION = ROOT / "out" / "x_session.json"
BASE = ROOT / "out" / "profiles"
KEYS = ("X_BOT_USERNAME", "X_BOT_EMAIL", "X_BOT_PASSWORD", "X_BOT_TOTP_SECRET", "X_BOT_PROXY")


def pick(name):
    d = BASE / re.sub(r"[^A-Za-z0-9_-]", "", name)
    if not d.name:
        raise SystemExit("name must be alphanumeric")
    return d


def read_env():
    return dict(l.split("=", 1) for l in ENV.read_text().splitlines() if "=" in l and not l.strip().startswith("#"))


def cmd_save(name):
    d = pick(name); d.mkdir(parents=True, exist_ok=True)
    e = read_env()
    (d / "env.txt").write_text("\n".join(f"{k}={e[k]}" for k in KEYS if k in e) + "\n")
    (d / "env.txt").chmod(0o600)
    if SESSION.exists():
        shutil.copy2(SESSION, d / "x_session.json")
    print(f"saved profile '{name}' to {d}")


def cmd_use(name):
    d = pick(name)
    if not (d / "env.txt").exists():
        raise SystemExit(f"no profile at {d}")
    new = dict(l.split("=", 1) for l in (d / "env.txt").read_text().splitlines() if "=" in l)
    lines = [l for l in (ENV.read_text().splitlines() if ENV.exists() else []) if l.split("=", 1)[0] not in KEYS]
    ENV.write_text("\n".join(lines + [f"{k}={new[k]}" for k in KEYS if k in new]) + "\n")
    ENV.chmod(0o600)
    if (d / "x_session.json").exists():
        SESSION.parent.mkdir(exist_ok=True); shutil.copy2(d / "x_session.json", SESSION)
    elif SESSION.exists():
        SESSION.unlink()
    print(f"loaded profile '{name}'. Next: python3 x_actions.py status")


def main():
    args = sys.argv[1:]
    if args[:1] == ["save"] and len(args) == 2: cmd_save(args[1])
    elif args[:1] == ["use"] and len(args) == 2: cmd_use(args[1])
    elif args == ["list"]:
        if not BASE.exists(): print("(no profiles)"); return
        for d in sorted(BASE.iterdir()):
            if d.is_dir(): print(" ", d.name)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
