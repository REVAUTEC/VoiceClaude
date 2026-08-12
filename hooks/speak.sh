#!/usr/bin/env bash
# voice-claude — Stop hook. Loop-safe: VŽDY exit 0, nic na stdout/stderr.
# Přečte last_assistant_message, vytáhne <voice> shrnutí, syntéza + přehrání na pozadí.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG="${XDG_CONFIG_HOME:-$HOME/.config}/voice-claude"
RUN="${XDG_RUNTIME_DIR:-/tmp}/voice-claude"
LOG="$CFG/voice-claude.log"
mkdir -p "$CFG" "$RUN" 2>/dev/null
chmod 700 "$RUN" 2>/dev/null
exec 2>>"$LOG"   # veškerý stderr do logu, nikdy ne Claudovi

PY="${VC_PYTHON:-python3}"
st() { "$PY" "$ROOT/scripts/state.py" "$@" 2>>"$LOG"; }
log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG" 2>/dev/null; }

{
  payload="$(cat)"

  # CC ≥2.1 nepředává ${user_config.*} interpolaci z hooks.json — options čteme sami ze settings.json.
  vc_opt() { jq -r ".pluginConfigs[\"voice-claude@voice-claude\"].options.$1 // empty" "$HOME/.claude/settings.json" 2>/dev/null; }
  [ -n "${CLAUDE_PLUGIN_OPTION_GOOGLEAPIKEY:-}" ] || export CLAUDE_PLUGIN_OPTION_GOOGLEAPIKEY="$(vc_opt googleApiKey)"
  [ -n "${CLAUDE_PLUGIN_OPTION_GENDER:-}" ] || export CLAUDE_PLUGIN_OPTION_GENDER="$(vc_opt gender)"
  [ -n "${CLAUDE_PLUGIN_OPTION_SPEAKINGRATE:-}" ] || export CLAUDE_PLUGIN_OPTION_SPEAKINGRATE="$(vc_opt speakingRate)"
  [ -n "${CLAUDE_PLUGIN_OPTION_MAXCHARS:-}" ] || export CLAUDE_PLUGIN_OPTION_MAXCHARS="$(vc_opt maxChars)"

  # Úklid starých audio souborů na začátku každého tahu (proběhne i při early-exitu).
  find "$RUN" -name 'out.*.wav' -mmin +5 -delete 2>/dev/null

  # Stav přečteme JEDNÍM voláním (hot path běží po každém tahu) a parsujeme jq.
  st_json="$(st getjson)"
  sv() { printf '%s' "$st_json" | jq -r "$1" 2>/dev/null; }

  [ "$(sv '.enabled')" = "true" ] || exit 0

  mute="$(sv '.muteRemaining // 0')"
  case "$mute" in ''|*[!0-9]*) mute=0 ;; esac
  if [ "$mute" -gt 0 ]; then
    st dec muteRemaining >/dev/null
    log "ztlumeno (zbývalo $mute)"
    exit 0
  fi

  # Délka shrnutí: "short" = jen 1. věta, "long" = celé <voice>.
  sl="$(sv '.summaryLength // empty')"
  export VC_SUMMARY="${sl:-long}"

  text=""
  msg="$(printf '%s' "$payload" | jq -r '.last_assistant_message // empty' 2>/dev/null)"
  if [ -n "$msg" ]; then
    text="$(printf '%s' "$msg" | "$PY" "$ROOT/scripts/resolve.py" 2>>"$LOG")"
  else
    tp="$(printf '%s' "$payload" | jq -r '.transcript_path // empty' 2>/dev/null)"
    if [ -n "$tp" ] && [ -f "$tp" ]; then
      text="$("$PY" "$ROOT/scripts/resolve.py" --from-transcript "$tp" 2>>"$LOG")"
    fi
  fi

  [ -n "$text" ] || { log "žádné <voice> shrnutí → ticho"; exit 0; }

  # Jazyk je napevno český. Hlas: 1) explicitně zvolený (/speak voice|gender),
  # jinak 2) podle pohlaví z userConfigu (default žena → Aoede).
  export VC_LANG="cs-CZ"
  vn="$(sv '.voiceName // empty')"
  if [ -z "$vn" ]; then
    case "${CLAUDE_PLUGIN_OPTION_GENDER:-žena}" in
      [mM]už|[mM]uz|muž|muz|male|Male|MALE|m|M|pán|pan) vn="cs-CZ-Chirp3-HD-Charon" ;;
      *) vn="cs-CZ-Chirp3-HD-Aoede" ;;
    esac
  fi
  export VC_VOICE="$vn"
  sr="$(sv '.speakingRate // empty')"
  export VC_RATE="${sr:-${CLAUDE_PLUGIN_OPTION_SPEAKINGRATE:-1.0}}"
  export VC_MAXCHARS="${CLAUDE_PLUGIN_OPTION_MAXCHARS:-1500}"

  out="$RUN/out.$$.wav"
  res="$(printf '%s' "$text" | timeout 20 "$PY" "$ROOT/scripts/tts.py" "$out" 2>>"$LOG")"
  case "$res" in
    OK*)
      [ -n "$(sv '.lastError // empty')" ] && st set lastError "" >/dev/null
      if [ -f "$RUN/play.pid" ]; then
        oldpid="$(cat "$RUN/play.pid" 2>/dev/null)"
        case "$oldpid" in ''|*[!0-9]*) ;; *) kill "$oldpid" 2>/dev/null ;; esac
      fi
      setsid "$ROOT/scripts/play.sh" "$out" </dev/null >/dev/null 2>&1 &
      echo $! > "$RUN/play.pid"
      log "mluvím: ${text:0:70}"
      ;;
    *)
      st set lastError "$res" >/dev/null
      log "TTS chyba: $res"
      ;;
  esac

  exit 0
} >>"$LOG" 2>&1

exit 0
