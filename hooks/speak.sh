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

  [ "$(st get enabled true)" = "true" ] || exit 0

  mute="$(st get muteRemaining 0)"
  case "$mute" in ''|*[!0-9]*) mute=0 ;; esac
  if [ "$mute" -gt 0 ]; then
    st dec muteRemaining >/dev/null
    log "ztlumeno (zbývalo $mute)"
    exit 0
  fi

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

  export VC_VOICE; VC_VOICE="$(st get voiceName "${CLAUDE_PLUGIN_OPTION_VOICENAME:-cs-CZ-Chirp3-HD-Achernar}")"
  export VC_LANG;  VC_LANG="$(st get languageCode "${CLAUDE_PLUGIN_OPTION_LANGUAGECODE:-cs-CZ}")"
  export VC_RATE;  VC_RATE="$(st get speakingRate "${CLAUDE_PLUGIN_OPTION_SPEAKINGRATE:-1.0}")"
  export VC_MAXCHARS="${CLAUDE_PLUGIN_OPTION_MAXCHARS:-1200}"

  out="$RUN/out.$$.wav"
  res="$(printf '%s' "$text" | timeout 20 "$PY" "$ROOT/scripts/tts.py" "$out" 2>>"$LOG")"
  case "$res" in
    OK*)
      st set lastError "" >/dev/null
      if [ -f "$RUN/play.pid" ]; then
        kill "$(cat "$RUN/play.pid" 2>/dev/null)" 2>/dev/null
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

  find "$RUN" -name 'out.*.wav' -mmin +5 -delete 2>/dev/null
  exit 0
} >>"$LOG" 2>&1

exit 0
