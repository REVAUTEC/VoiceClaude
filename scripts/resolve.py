#!/usr/bin/env python3
"""voice-claude — vytáhne mluvené shrnutí z <voice>...</voice>.

Vstup:
    stdin                       = text odpovědi Claude
    --from-transcript <path>    = JSONL transcript (vezme poslední assistant zprávu)

Pravidlo (spec 14.2): nejdřív odstraní bloky kódu, pak vezme POSLEDNÍ neprázdný
<voice>...</voice> (vyžaduje oba tagy). Když validní tag chybí → nevypíše NIC
(= ticho; žádné čtení začátku těla odpovědi).
"""
import sys
import os
import re
import json

MAXCHARS = 1500
try:
    _m = int(os.environ.get("VC_MAXCHARS") or MAXCHARS)
    if _m > 0:  # záporné/nulové by přes text[:MAXCHARS] uřízlo konec nebo vše
        MAXCHARS = _m
except ValueError:
    pass

FENCE = re.compile(r"```.*?```", re.S)
VOICE = re.compile(r"<voice>(.*?)</voice>", re.I | re.S)


def last_assistant_from_transcript(path):
    text = ""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                msg = obj.get("message") if isinstance(obj, dict) else None
                if not isinstance(msg, dict) or msg.get("role") != "assistant":
                    continue
                content = msg.get("content")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    parts = [
                        b.get("text", "")
                        for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    ]
                    if parts:
                        text = "".join(parts)
    except Exception:
        return ""
    return text


def extract(raw):
    if not raw:
        return ""
    no_code = FENCE.sub(" ", raw)  # <voice> uvnitř ukázky kódu se nezapočítá
    matches = [m.strip() for m in VOICE.findall(no_code) if m.strip()]
    if not matches:
        return ""
    text = re.sub(r"\s+", " ", matches[-1]).strip()
    return text[:MAXCHARS]


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--from-transcript":
        raw = last_assistant_from_transcript(sys.argv[2])
    else:
        raw = sys.stdin.read()
    out = extract(raw)
    if out:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
