#!/bin/zsh
set -euo pipefail

repo=/Users/prithiraj/sinclair-x-bot
cd "$repo"
/usr/bin/python3 orbit.py check

target="${HOME}/Library/LaunchAgents"
mkdir -p "$target"
for name in mega-post mega-engage likes; do
  label="com.sinclair.orbit-${name}"
  source="$repo/launchd/${label}.plist"
  /usr/bin/plutil -lint "$source"
  cp "$source" "$target/${label}.plist"
  if ! launchctl print "gui/$(id -u)/${label}" >/dev/null 2>&1; then
    launchctl bootstrap "gui/$(id -u)" "$target/${label}.plist"
  fi
done
echo 'Engage-Orbit jobs installed and loaded.'
