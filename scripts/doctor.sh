#!/usr/bin/env bash
# voice-claude — preflight diagnostika.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${VC_PYTHON:-python3}"
ok()  { printf '  ✅ %s\n' "$*"; }
bad() { printf '  ❌ %s\n' "$*"; }

echo "voice-claude doctor:"
command -v "$PY" >/dev/null 2>&1 && ok "python3" || bad "python3 chybí"
command -v jq >/dev/null 2>&1 && ok "jq" || bad "jq chybí (nutné pro Stop hook — čtení stavu a odpovědi)"

# Vyber přehrávač stejně jako play.sh: pw-play přeskoč, když PipeWire server neběží
# (např. WSLg má jen PulseAudio → pw-play by selhal "Host is down").
P=""
for p in pw-play paplay ffplay aplay mpv; do
  if command -v "$p" >/dev/null 2>&1; then
    if [ "$p" = "pw-play" ] && [ ! -S "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/pipewire-0" ]; then
      continue
    fi
    P="$p"; break
  fi
done
if [ -n "$P" ]; then
  ok "přehrávač: $P"
  [ "$P" = "ffplay" ] && printf '  ⚠️  %s\n' "ffplay může ve WSLg praskat (buffer underrun). Pro čistý zvuk: 'sudo apt install pulseaudio-utils' (paplay)."
else
  bad "žádný použitelný přehrávač (nainstaluj pulseaudio-utils → paplay, nebo ffmpeg → ffplay)"
fi

keyfound="$("$PY" - <<'PYEOF'
import os
def has():
    if os.environ.get("GOOGLE_API_KEY"):
        return True
    for n, v in os.environ.items():
        if v and n.startswith("CLAUDE_PLUGIN_OPTION_") \
                and n[len("CLAUDE_PLUGIN_OPTION_"):].replace("_", "").lower() == "googleapikey":
            return True
    return False
print("yes" if has() else "no")
PYEOF
)"
if [ "$keyfound" = "yes" ]; then
  ok "API klíč nalezen v prostředí"
else
  printf '  ℹ️  %s\n' "API klíč z instalace (userConfig) se předává přímo Stop hooku — doctor ho odsud nevidí, to je OK."
  printf '      %s\n' "Ověř odesláním zprávy; chyba klíče by se ukázala níže u 'poslední TTS chyba'."
fi
# Diagnostika: které plugin-option proměnné tento podproces vidí (jen názvy, ne hodnoty).
"$PY" - <<'PYEOF'
import os
ks = sorted(k for k in os.environ if k.startswith("CLAUDE_PLUGIN_OPTION_"))
print("  plugin options v env:", (", ".join(ks) if ks else "(žádné — userConfig se do tohoto podprocesu nepředává)"))
PYEOF

echo "  stav: $("$PY" "$ROOT/scripts/state.py" getjson 2>/dev/null)"
le="$("$PY" "$ROOT/scripts/state.py" get lastError "" 2>/dev/null)"
[ -n "$le" ] && bad "poslední TTS chyba: $le" || ok "žádná poslední TTS chyba"
