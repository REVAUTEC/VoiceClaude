#!/usr/bin/env bash
# voice-claude — preflight diagnostika.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${VC_PYTHON:-python3}"
ok()  { printf '  ✅ %s\n' "$*"; }
bad() { printf '  ❌ %s\n' "$*"; }

echo "voice-claude doctor:"
command -v "$PY" >/dev/null 2>&1 && ok "python3" || bad "python3 chybí"

P=""
for p in pw-play paplay aplay ffplay mpv mpg123; do
  if command -v "$p" >/dev/null 2>&1; then P="$p"; break; fi
done
[ -n "$P" ] && ok "přehrávač: $P" || bad "žádný přehrávač (nainstaluj mpv nebo pw-play/aplay)"

if [ -n "${CLAUDE_PLUGIN_OPTION_GOOGLEAPIKEY:-}${CLAUDE_PLUGIN_OPTION_GOOGLE_API_KEY:-}${GOOGLE_API_KEY:-}" ]; then
  ok "API klíč v env (nalezen)"
else
  bad "API klíč nenalezen (userConfig googleApiKey nebo env GOOGLE_API_KEY)"
fi

echo "  stav: $("$PY" "$ROOT/scripts/state.py" getjson 2>/dev/null)"
le="$("$PY" "$ROOT/scripts/state.py" get lastError "" 2>/dev/null)"
[ -n "$le" ] && bad "poslední TTS chyba: $le" || ok "žádná poslední TTS chyba"
