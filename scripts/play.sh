#!/usr/bin/env bash
# voice-claude — přehraje audio soubor prvním dostupným přehrávačem. $1 = soubor.
f="$1"
[ -f "$f" ] || exit 0
if   command -v pw-play >/dev/null 2>&1; then exec pw-play "$f"
elif command -v paplay  >/dev/null 2>&1; then exec paplay "$f"
elif command -v aplay   >/dev/null 2>&1; then exec aplay -q "$f"
elif command -v ffplay  >/dev/null 2>&1; then exec ffplay -nodisp -autoexit -loglevel quiet "$f"
elif command -v mpv     >/dev/null 2>&1; then exec mpv --no-video --really-quiet "$f"
else exit 0
fi
