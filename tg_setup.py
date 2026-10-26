"""One-time Telegram login via Telethon. Saves a session file so later runs are headless.

  python3 tg_setup.py

Prompts for api_id, api_hash (from https://my.telegram.org), phone, and the SMS/app code.
Writes TG_API_ID, TG_API_HASH, TG_PHONE to .env (gitignored), and out/telegram.session.
"""
import asyncio
import getpass
import os
import re
from pathlib import Path
from telethon import TelegramClient

ROOT = Path(__file__).parent
ENV = ROOT / ".env"
SESSION = ROOT / "out" / "telegram"
KEYS = ("TG_API_ID", "TG_API_HASH", "TG_PHONE")


def load_env():
    if ENV.exists():
        for l in ENV.read_text().splitlines():
            if "=" in l and not l.lstrip().startswith("#"):
                k, v = l.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def save_env(vals):
    lines = [l for l in (ENV.read_text().splitlines() if ENV.exists() else []) if l.split("=", 1)[0] not in vals]
    ENV.write_text("\n".join(lines + [f"{k}={v}" for k, v in vals.items()]) + "\n")
    ENV.chmod(0o600)


async def main():
    load_env()
    vals = {}
    if not os.getenv("TG_API_ID"):
        vals["TG_API_ID"] = input("api_id (number from my.telegram.org): ").strip()
        if not vals["TG_API_ID"].isdigit():
            raise SystemExit("api_id must be a number")
    if not os.getenv("TG_API_HASH"):
        v = getpass.getpass("api_hash (32-char hex, hidden): ").strip()
        if not re.fullmatch(r"[0-9a-f]{32}", v):
            raise SystemExit("api_hash must be 32 hex chars")
        vals["TG_API_HASH"] = v
    if not os.getenv("TG_PHONE"):
        v = input("phone with country code (e.g. +919876543210): ").strip()
        if not re.fullmatch(r"\+\d{7,15}", v):
            raise SystemExit("phone must look like +919876543210")
        vals["TG_PHONE"] = v
    if vals:
        save_env(vals)
        load_env()
    SESSION.parent.mkdir(exist_ok=True)
    client = TelegramClient(str(SESSION), int(os.getenv("TG_API_ID")), os.getenv("TG_API_HASH"))
    await client.start(phone=os.getenv("TG_PHONE"))
    me = await client.get_me()
    print(f"logged in as @{me.username or me.first_name}. Session saved to {SESSION}.session")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
