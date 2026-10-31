#!/bin/zsh
set -euo pipefail
# launchd starts without Homebrew on PATH; the Codex CLI requires Node.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
repo=/Users/prithiraj/sinclair-x-bot
mkdir -p "$repo/out"
cd "$repo"
exec /usr/bin/python3 scheduled_run.py daily >> "$repo/out/codex_draft.log" 2>&1
