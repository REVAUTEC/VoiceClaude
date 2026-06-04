#!/usr/bin/env python3
"""voice-claude — atomický stav v ~/.config/voice-claude/state.json.

Použití:
    state.py get <klíč> [default]   # vytiskne hodnotu (bool jako true/false)
    state.py getjson                # celý stav jako JSON
    state.py set <klíč> <hodnota>   # atomicky uloží (typy se odvodí)
    state.py dec <klíč>             # dekrementuje int (min 0), vytiskne novou hodnotu
"""
import sys
import os
import json
import math
import tempfile

# VC_STATE_FILE umožní nasměrovat na konkrétní soubor (např. když panel běží jako
# nativní Windows proces a sahá do WSL stavu přes \\wsl.localhost\… cestu).
_OVERRIDE = os.environ.get("VC_STATE_FILE")
if _OVERRIDE:
    STATE_FILE = _OVERRIDE
    STATE_DIR = os.path.dirname(_OVERRIDE) or "."
else:
    STATE_DIR = os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
        "voice-claude",
    )
    STATE_FILE = os.path.join(STATE_DIR, "state.json")
DEFAULTS = {
    "enabled": True,
    "gender": None,
    "voiceName": None,
    "speakingRate": None,
    "muteRemaining": 0,
    "lastError": "",
    "summaryLength": "long",     # "short" = jen 1. věta <voice>, "long" = celé
    "panelOrientation": "h",     # plovoucí panel: "h" vodorovně / "v" svisle
    "panelTheme": "auto",        # panel: "auto" (dle OS) / "dark" / "light"
    "panelAlpha": 1.0,           # panel: průhlednost 1.0 = plné, 0.5 = 50 %
    "panelOnTop": True,          # panel: vždy navrchu (always-on-top) zap/vyp
}


def load():
    data = {}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data = loaded
    except Exception:
        pass
    out = dict(DEFAULTS)
    out.update({k: v for k, v in data.items() if k in DEFAULTS})
    return out


def save(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        os.replace(tmp, STATE_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def coerce(v):
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none", ""):
        return None
    try:
        return int(v)
    except ValueError:
        try:
            f = float(v)
        except ValueError:
            return v
        # inf/nan by se uložily jako neplatný JSON (Infinity/NaN) a rozbily jq
        # čtení stavu v hooku → ponecháme jako řetězec.
        return f if math.isfinite(f) else v


def main():
    args = sys.argv[1:]
    if not args:
        return
    cmd = args[0]
    state = load()
    if cmd == "get":
        if len(args) < 2:
            return
        key = args[1]
        default = args[2] if len(args) > 2 else ""
        v = state.get(key)
        if v is None:
            print(default)
        elif isinstance(v, bool):
            print("true" if v else "false")
        else:
            print(v)
    elif cmd == "getjson":
        print(json.dumps(state, ensure_ascii=False))
    elif cmd == "set":
        if len(args) < 3:
            return
        state[args[1]] = coerce(args[2])
        save(state)
    elif cmd == "dec":
        if len(args) < 2:
            return
        try:
            cur = int(state.get(args[1]) or 0)
        except (TypeError, ValueError):
            cur = 0
        state[args[1]] = max(0, cur - 1)
        save(state)
        print(state[args[1]])


if __name__ == "__main__":
    main()
