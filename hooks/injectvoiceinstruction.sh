#!/usr/bin/env bash
# voice-claude — SessionStart hook. Když je hlas zapnutý, vloží Claudovi instrukci,
# aby na konec běžných odpovědí přidával <voice>…</voice> s mluveným shrnutím.
# Context-gating: instrukce sama říká, ať tag NEPŘIDÁVÁ do JSON/jury/klientských výstupů.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG="${XDG_CONFIG_HOME:-$HOME/.config}/voice-claude"
LOG="$CFG/voice-claude.log"
mkdir -p "$CFG" 2>/dev/null
exec 2>>"$LOG"

PY="${VC_PYTHON:-python3}"
[ "$("$PY" "$ROOT/scripts/state.py" get enabled true 2>>"$LOG")" = "true" ] || exit 0

INSTR='voice-claude: Na úplný konec každé své běžné konverzační odpovědi přidej blok <voice>…</voice> s 1–3 větami českého MLUVENÉHO shrnutí hlavního sdělení. Piš přirozenou mluvenou češtinou, bez kódu, cest, příkazů a URL. Pokud generuješ strukturovaný výstup (JSON, jury verdikt, phase output), klientský e-mail či dokument, nebo jednáš jako subagent ve formální roli, blok <voice> NEPŘIDÁVEJ.'

"$PY" - "$INSTR" <<'PY' 2>>"$LOG"
import sys, json
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": sys.argv[1],
    }
}, ensure_ascii=False))
PY
exit 0
