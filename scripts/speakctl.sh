#!/usr/bin/env bash
# voice-claude — ovládání pro /speak. Vytiskne lidsky čitelný výsledek.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${VC_PYTHON:-python3}"
st() { "$PY" "$ROOT/scripts/state.py" "$@"; }

cmd="${1:-status}"
[ $# -gt 0 ] && shift

case "$cmd" in
  on)
    st set enabled true; st set muteRemaining 0
    echo "🔊 voice-claude zapnut." ;;
  off)
    st set enabled false
    echo "🔇 voice-claude vypnut (/speak on pro obnovení)." ;;
  mute)
    n="${1:-}"
    if [ -z "$n" ]; then
      st set muteRemaining 999999
      echo "🔇 ztlumeno do /speak on."
    else
      case "$n" in ''|*[!0-9]*) echo "Použití: /speak mute <počet tahů>"; exit 0 ;; esac
      st set muteRemaining "$n"
      echo "🔇 ztlumeno na dalších $n tahů, pak se hlas sám zapne."
    fi ;;
  voice)
    if [ -n "$1" ]; then st set voiceName "$1"; echo "🎙️ hlas = $1"
    else echo "Použití: /speak voice <jméno>  (např. cs-CZ-Chirp3-HD-Achernar)"; fi ;;
  rate)
    if [ -z "$1" ]; then
      echo "Použití: /speak rate <0.25–2.0>"
    elif "$PY" -c "import sys; r=float(sys.argv[1]); sys.exit(0 if 0.25<=r<=2.0 else 1)" "$1" 2>/dev/null; then
      st set speakingRate "$1"; echo "⏩ tempo = $1"
    else
      echo "Neplatné tempo '$1'. Zadej číslo v rozsahu 0.25–2.0."
    fi ;;
  doctor)
    bash "$ROOT/scripts/doctor.sh" ;;
  status)
    echo "voice-claude stav:"
    st getjson ;;
  *)
    echo "Neznámý příkaz '$cmd'. Použij: status | on | off | mute [n] | voice <jméno> | rate <x> | doctor" ;;
esac
