"""Authorize the Telegram user session by scanning a QR code on a phone.

Run `python3 tg_qr_setup.py`, then in Telegram on the phone open
Settings > Devices > Link Desktop Device and scan the QR shown in Chrome.
"""

import asyncio
import getpass
import os
import subprocess
from pathlib import Path

import cv2
from telethon import TelegramClient, errors

from tg_setup import ROOT, SESSION, load_env


QR_FILE = ROOT / "out" / "telegram-login-qr.png"
PAGE_FILE = ROOT / "out" / "telegram-login-qr.html"


def show_qr(url):
    encoder = cv2.QRCodeEncoder_create()
    qr = encoder.encode(url)
    qr = cv2.copyMakeBorder(qr, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
    qr = cv2.resize(qr, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST)
    tmp = QR_FILE.with_suffix(".tmp.png")
    if not cv2.imwrite(str(tmp), qr):
        raise RuntimeError("Could not write QR image")
    tmp.chmod(0o600)
    tmp.replace(QR_FILE)


def open_page():
    PAGE_FILE.write_text('''<!doctype html><html><head><meta charset="utf-8">
<title>Telegram QR login</title><meta name="viewport" content="width=device-width">
<style>body{font:18px system-ui;text-align:center;padding:30px;background:#f5f5f5}
img{width:min(75vw,560px);image-rendering:pixelated}</style></head><body>
<h1>Scan with Telegram on your phone</h1>
<p>Settings → Devices → Link Desktop Device</p>
<img id="qr" alt="Telegram login QR code">
<p>Keep this page open until Terminal says logged in.</p>
<script>setInterval(()=>document.getElementById('qr').src=
'telegram-login-qr.png?t='+Date.now(),1000)</script></body></html>''')
    PAGE_FILE.chmod(0o600)
    subprocess.run(["open", "-a", "Google Chrome", str(PAGE_FILE)], check=True)


async def main():
    load_env()
    if not os.getenv("TG_API_ID") or not os.getenv("TG_API_HASH"):
        raise SystemExit("Run python3 tg_setup.py once to save the Telegram API ID and hash")
    SESSION.parent.mkdir(exist_ok=True)
    client = TelegramClient(str(SESSION), int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"])
    try:
        await client.connect()
        if not await client.is_user_authorized():
            qr_login = await client.qr_login()
            show_qr(qr_login.url)
            open_page()
            print("Scan the QR in Chrome from Telegram on your phone: Settings > Devices > Link Desktop Device.", flush=True)
            while True:
                try:
                    await qr_login.wait()
                    break
                except asyncio.TimeoutError:
                    await qr_login.recreate()
                    show_qr(qr_login.url)
                    print("QR refreshed; scan the new code in Chrome.", flush=True)
                except errors.SessionPasswordNeededError:
                    password = getpass.getpass("Telegram two-step verification password: ")
                    await client.sign_in(password=password)
                    break
        me = await client.get_me()
        print(f"logged in as @{me.username or me.first_name}. Session saved to {SESSION}.session", flush=True)
    finally:
        await client.disconnect()
        QR_FILE.unlink(missing_ok=True)
        PAGE_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
