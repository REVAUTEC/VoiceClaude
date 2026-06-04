#!/usr/bin/env bash
# voice-claude — přehraje audio soubor prvním dostupným přehrávačem. $1 = soubor.
f="$1"
[ -f "$f" ] || exit 0
# Výběr přehrávače:
# - Ve WSLg jde zvuk spolehlivě jen přes PulseAudio most /mnt/wslg/PulseServer.
#   PipeWire tam sice MŮŽE běžet (socket pipewire-0 existuje), ale jeho výstup se
#   nedostane do WSLg RDP sinku → pw-play vrátí 0, ale je TICHO. Proto ve WSLg
#   pw-play přeskoč a použij paplay (nativní pulse, čistý) / ffplay.
# - Mimo WSLg použij pw-play, pokud PipeWire reálně běží (socket pipewire-0).
pipewire_ok() { [ -S "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/pipewire-0" ] && [ ! -S /mnt/wslg/PulseServer ]; }
if   command -v pw-play >/dev/null 2>&1 && pipewire_ok; then exec pw-play "$f"
elif command -v paplay  >/dev/null 2>&1; then exec paplay "$f"
elif command -v ffplay  >/dev/null 2>&1; then exec ffplay -nodisp -autoexit -loglevel quiet "$f"
elif command -v aplay   >/dev/null 2>&1; then exec aplay -q "$f"
elif command -v pw-play >/dev/null 2>&1 && [ -S "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/pipewire-0" ]; then exec pw-play "$f"
elif command -v mpv     >/dev/null 2>&1; then exec mpv --no-video --really-quiet "$f"
else exit 0
fi
