---
description: Ovládá voice-claude (předčítání odpovědí) — status/on/off/short/long/voice/rate/panel/revive/doctor
argument-hint: "[status | on | off | toggle | short | long | mute <n> | voice <jméno> | rate <0.25-2.0> | panel | revive | doctor]"
allowed-tools: Bash
---

Uživatel chce ovládat plugin voice-claude. Spusť přesně tento příkaz přes Bash
a uživateli stručně vypiš jeho výstup (nic víc nepřidávej):

`"${CLAUDE_PLUGIN_ROOT}/scripts/speakctl.sh" $ARGUMENTS`
