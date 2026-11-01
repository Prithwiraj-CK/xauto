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
  installed="$target/${label}.plist"
  /usr/bin/plutil -lint "$source"
  if [[ ! -f "$installed" ]] || ! cmp -s "$source" "$installed"; then
    if launchctl print "gui/$(id -u)/${label}" >/dev/null 2>&1; then
      launchctl bootout "gui/$(id -u)/${label}"
    fi
    cp "$source" "$installed"
  fi
  if ! launchctl print "gui/$(id -u)/${label}" >/dev/null 2>&1; then
    launchctl bootstrap "gui/$(id -u)" "$installed"
  fi
done
echo 'Engage-Orbit jobs installed and loaded.'
