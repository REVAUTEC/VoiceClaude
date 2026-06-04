#!/usr/bin/env python3
"""voice-claude — české Chirp 3 HD hlasy a mapování pohlaví → jméno.

Napevno: jazyk cs-CZ, engine Chirp 3 HD. Nabízíme hlasy s jistým pohlavím.

Použití:
    voices.py gender <muž|žena>   # vytiskne plný název výchozího hlasu pro pohlaví
    voices.py expand <jméno>      # krátké jméno (Aoede) → cs-CZ-Chirp3-HD-Aoede; neznámé → prázdné
    voices.py normgender <text>   # 'male' / 'female'
    voices.py list                # vypíše hlasy podle pohlaví
"""
import sys

PREFIX = "cs-CZ-Chirp3-HD-"
FEMALE = ["Aoede", "Kore", "Leda", "Zephyr"]
MALE = ["Puck", "Charon", "Fenrir", "Orus"]
ALL = FEMALE + MALE
DEFAULT = {"female": "Aoede", "male": "Charon"}


def norm_gender(g):
    g = (g or "").strip().lower()
    if g in ("muž", "muz", "male", "m", "pán", "pan", "chlap", "man"):
        return "male"
    return "female"  # default je žena


def voice_for_gender(g):
    return PREFIX + DEFAULT[norm_gender(g)]


def expand(name):
    name = (name or "").strip()
    if not name:
        return ""
    short = name.replace(PREFIX, "")
    for v in ALL:
        if v.lower() == short.lower():
            return PREFIX + v
    return ""  # neznámé jméno


def main():
    args = sys.argv[1:]
    if not args:
        return
    cmd = args[0]
    if cmd == "gender" and len(args) > 1:
        print(voice_for_gender(args[1]))
    elif cmd == "expand" and len(args) > 1:
        print(expand(args[1]))
    elif cmd == "normgender" and len(args) > 1:
        print(norm_gender(args[1]))
    elif cmd == "list":
        print("  žena: " + ", ".join(FEMALE))
        print("  muž:  " + ", ".join(MALE))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
