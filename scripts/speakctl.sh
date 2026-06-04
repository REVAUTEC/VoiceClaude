#!/usr/bin/env bash
# voice-claude — ovládání pro /speak. Vytiskne lidsky čitelný výsledek.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${VC_PYTHON:-python3}"
st() { "$PY" "$ROOT/scripts/state.py" "$@"; }
vx() { "$PY" "$ROOT/scripts/voices.py" "$@"; }

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
  gender)
    if [ -z "$1" ]; then
      echo "Použití: /speak gender <žena|muž>"
    else
      g="$(vx normgender "$1")"
      v="$(vx gender "$1")"
      st set gender "$g"; st set voiceName "$v"
      echo "🎙️ pohlaví = $([ "$g" = male ] && echo muž || echo žena), hlas = $v"
      echo "   (konkrétní jméno: /speak voice <jméno> | seznam: /speak voices)"
    fi ;;
  voice)
    if [ -z "$1" ]; then
      echo "Dostupné české Chirp 3 HD hlasy:"
      vx list
      echo "Použij např.: /speak voice Aoede"
    else
      full="$(vx expand "$1")"
      if [ -n "$full" ]; then
        st set voiceName "$full"; echo "🎙️ hlas = $full"
      else
        echo "Neznámý hlas '$1'. Vyber z:"
        vx list
      fi
    fi ;;
  voices)
    echo "Dostupné české Chirp 3 HD hlasy:"
    vx list ;;
  rate)
    if [ -z "$1" ]; then
      echo "Použití: /speak rate <0.25–2.0>"
    elif "$PY" -c "import sys; r=float(sys.argv[1]); sys.exit(0 if 0.25<=r<=2.0 else 1)" "$1" 2>/dev/null; then
      st set speakingRate "$1"; echo "⏩ tempo = $1"
    else
      echo "Neplatné tempo '$1'. Zadej číslo v rozsahu 0.25–2.0."
    fi ;;
  toggle)
    if [ "$(st get enabled)" = "true" ]; then
      st set enabled false; echo "🔇 voice-claude vypnut."
    else
      st set enabled true; st set muteRemaining 0; echo "🔊 voice-claude zapnut."
    fi ;;
  short)
    st set summaryLength short
    echo "✍ délka = krátké (přečte jen 1. větu shrnutí)." ;;
  long)
    st set summaryLength long
    echo "✍ délka = dlouhé (přečte celé <voice> shrnutí)." ;;
  length)
    if [ "$(st get summaryLength)" = "short" ]; then
      st set summaryLength long; echo "✍ délka = dlouhé."
    else
      st set summaryLength short; echo "✍ délka = krátké."
    fi ;;
  panel)
    if "$PY" -c "import tkinter" 2>/dev/null; then
      nohup "$PY" "$ROOT/scripts/panel.py" >/dev/null 2>&1 &
      echo "🪟 panel spuštěn (plovoucí ikonová lišta, always-on-top)."
      "$PY" -c "import PIL" 2>/dev/null || \
        echo "   tip: pro hladké (anti-aliasované) ikony nainstaluj Pillow: pip install pillow"
      echo "   Pokud se neukázal: WSL → potřebuješ Windows 11 (WSLg) a 'sudo apt install python3-tk';"
      echo "   nejjistější je spustit ho z vlastního terminálu: $PY \"$ROOT/scripts/panel.py\" &"
    else
      echo "Chybí Tkinter (GUI knihovna)."
      echo "   Ubuntu/WSL: sudo apt install python3-tk"
      echo "   macOS: bývá součástí Pythonu z python.org (nebo: brew install python-tk)"
    fi ;;
  doctor)
    bash "$ROOT/scripts/doctor.sh" ;;
  status)
    echo "voice-claude stav:"
    st getjson ;;
  *)
    echo "Neznámý příkaz '$cmd'. Použij: status | on | off | toggle | mute [n] | short | long | length | gender <žena|muž> | voice [jméno] | voices | rate <x> | panel | doctor" ;;
esac
