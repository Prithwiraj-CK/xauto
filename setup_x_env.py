"""Prompt for the X_BOT_* secrets and write them to .env (gitignored). Passwords are typed hidden, nothing is printed back.

  python3 setup_x_env.py          -> all values
  python3 setup_x_env.py totp     -> only replace the 2FA secret
"""
import getpass
import re
import sys
from pathlib import Path

ENV = Path(__file__).parent / ".env"
ASK = [("X_BOT_USERNAME", "secondary account username (no @)", False),
       ("X_BOT_EMAIL", "that account's email", False),
       ("X_BOT_PASSWORD", "that account's password (hidden)", True),
       ("X_BOT_TOTP_SECRET", "2FA secret key, the long base32 text, not the 6-digit code (hidden)", True)]


def save(vals):
    lines = [l for l in (ENV.read_text().splitlines() if ENV.exists() else []) if l.split("=", 1)[0] not in vals]
    ENV.write_text("\n".join(lines + [f"{k}={v}" for k, v in vals.items()]) + "\n")
    ENV.chmod(0o600)


def main():
    vals = {}
    only_totp = len(sys.argv) > 1 and sys.argv[1] == "totp"  # replace just the 2FA secret, keep everything else
    for key, label, hidden in (ASK[-1:] if only_totp else ASK):
        v = (getpass.getpass if hidden else input)(f"{label}: ").strip().replace(" ", "")
        if not v:
            raise SystemExit(f"{key} was empty, nothing written")
        vals[key] = v
    if not re.fullmatch(r"[A-Za-z2-7]{16,}", vals["X_BOT_TOTP_SECRET"]):
        raise SystemExit("that doesn't look like a base32 2FA secret (letters A-Z and digits 2-7, 16+ characters)")
    if only_totp:
        save(vals)
        print("\n2FA secret updated in .env, everything else kept. Next: python3 x_actions.py status")
        return
    print("\nWebshare proxy: copy the four values from Proxy List")
    host, port = input("IP / host: ").strip(), input("port: ").strip()
    user, pw = input("proxy username: ").strip(), getpass.getpass("proxy password (hidden): ").strip()
    if not (host and port.isdigit() and user and pw):
        raise SystemExit("proxy values incomplete, nothing written")
    vals["X_BOT_PROXY"] = f"http://{user}:{pw}@{host}:{port}"

    save(vals)
    print("\nsaved to .env. Next: python3 x_actions.py status")


if __name__ == "__main__":
    main()
