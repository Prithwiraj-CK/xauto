#!/bin/zsh
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
repo=/Users/prithiraj/sinclair-x-bot
mkdir -p "$repo/out"
cd "$repo"
exec /usr/bin/python3 scheduled_run.py replies >> "$repo/out/codex_replies.log" 2>&1
