#!/usr/bin/env bash
# voice-claude — přehraje audio soubor prvním dostupným přehrávačem. $1 = soubor.
f="$1"
[ -f "$f" ] || exit 0
# pw-play použij jen když PipeWire server reálně běží. Ve WSLg (jen PulseAudio přes
# /mnt/wslg/PulseServer) PipeWire socket chybí a pw-play selže s
# "pw_context_connect() failed: Host is down" → zvuk se tiše zahodí. V tom případě
# padáme na paplay (nativní pulse klient, čistý) a teprve pak ffplay.
if   command -v pw-play >/dev/null 2>&1 && [ -S "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/pipewire-0" ]; then exec pw-play "$f"
elif command -v paplay  >/dev/null 2>&1; then exec paplay "$f"
elif command -v ffplay  >/dev/null 2>&1; then exec ffplay -nodisp -autoexit -loglevel quiet "$f"
elif command -v aplay   >/dev/null 2>&1; then exec aplay -q "$f"
elif command -v mpv     >/dev/null 2>&1; then exec mpv --no-video --really-quiet "$f"
else exit 0
fi
