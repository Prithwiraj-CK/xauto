#!/bin/zsh
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd /Users/prithiraj/sinclair-x-bot
exec /usr/bin/python3 orbit.py "$@" >> out/orbit.log 2>&1
