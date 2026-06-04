#!/usr/bin/env python3
"""voice-claude — TTS: text (stdin) -> WAV (argv[1]) přes Cloud TTS Chirp HD.

Auth: API klíč z env (v pořadí):
    CLAUDE_PLUGIN_OPTION_GOOGLEAPIKEY | CLAUDE_PLUGIN_OPTION_GOOGLE_API_KEY | GOOGLE_API_KEY
Klíč se NIKDY netiskne (a z chyb se redaktuje). Jen stdlib.
Stdout: 'OK bytes=N' nebo 'ERR ...'. Exit 0 = OK, jinak nenulový.
"""
import sys
import os
import json
import math
import time
import base64
import urllib.request
import urllib.error

RETRYABLE = {429, 500, 502, 503, 504}


def getkey():
    # Přímá proměnná prostředí má přednost.
    if os.environ.get("GOOGLE_API_KEY"):
        return os.environ["GOOGLE_API_KEY"]
    # Klíč z userConfig: Claude Code nezaručuje casing názvu proměnné
    # (GOOGLEAPIKEY / GOOGLE_API_KEY / googleApiKey …), proto hledáme libovolnou
    # CLAUDE_PLUGIN_OPTION_* proměnnou, jejíž název odpovídá 'googleapikey'.
    for name, val in os.environ.items():
        # '${' = nedosazená šablona (substituce selhala) → ignorovat.
        if val and "${" not in val and name.startswith("CLAUDE_PLUGIN_OPTION_"):
            norm = name[len("CLAUDE_PLUGIN_OPTION_"):].replace("_", "").lower()
            if norm == "googleapikey":
                return val
    return ""


KEY = getkey()
OUT = sys.argv[1] if len(sys.argv) > 1 else "out.wav"
VOICE = os.environ.get("VC_VOICE") or "cs-CZ-Chirp3-HD-Achernar"
LANG = os.environ.get("VC_LANG") or "cs-CZ"
try:
    RATE = float(os.environ.get("VC_RATE") or 1.0)
except ValueError:
    RATE = 1.0
if not math.isfinite(RATE):  # inf/nan by se serializovaly jako neplatný JSON → 400
    RATE = 1.0
RATE = max(0.25, min(2.0, RATE))  # Google akceptuje jen tento rozsah


def redact(s):
    return s.replace(KEY, "***") if KEY else s


text = sys.stdin.read().strip()
if not text:
    print("ERR empty-text")
    sys.exit(1)
if not KEY:
    print("ERR no-api-key")
    sys.exit(1)

body = json.dumps({
    "input": {"text": text},
    "voice": {"languageCode": LANG, "name": VOICE},
    "audioConfig": {"audioEncoding": "LINEAR16", "speakingRate": RATE},
}).encode("utf-8")
req = urllib.request.Request(
    "https://texttospeech.googleapis.com/v1/text:synthesize",
    data=body,
    headers={"Content-Type": "application/json; charset=utf-8",
             "x-goog-api-key": KEY},
    method="POST",
)

last = "ERR unknown"
for attempt in (1, 2):
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            audio = base64.b64decode(json.loads(r.read())["audioContent"])
        with open(OUT, "wb") as f:
            f.write(audio)
        print(f"OK bytes={len(audio)}")
        sys.exit(0)
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode("utf-8", "replace")).get("error", {})
            last = redact(f"ERR http={e.code} status={j.get('status', '')} "
                          f"msg={j.get('message', '')}")
        except Exception:
            last = f"ERR http={e.code}"
        if e.code in RETRYABLE and attempt == 1:
            time.sleep(0.5)
            continue
        print(last)
        sys.exit(2)
    except urllib.error.URLError as e:
        last = redact(f"ERR net={e.reason}")
        if attempt == 1:
            time.sleep(0.5)
            continue
        print(last)
        sys.exit(3)
    except Exception as e:  # noqa: BLE001
        print(redact(f"ERR {type(e).__name__}"))
        sys.exit(4)

print(last)
sys.exit(2)
