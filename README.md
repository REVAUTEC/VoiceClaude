# voice-claude

Claude Code plugin, který **nahlas předčítá mluvené shrnutí** každé odpovědi Claude
přes **Google Cloud Text-to-Speech (Chirp 3 HD)** — primárně **česky**, hlas
`cs-CZ-Chirp3-HD-Achernar`.

Shrnutí píše sám Claude do tagu `<voice>…</voice>` na konci odpovědi (žádný druhý
LLM krok → nulová extra latence). Plugin přečte jen obsah tagu. Čte se **až po
úplném dokončení** odpovědi (Stop hook), nikdy během psaní.

## ⚡ Instalace ve 3 krocích

> Potřebuješ jen Claude Code, `python3`, `jq`, audio přehrávač a Google API klíč
> s povoleným **Cloud Text-to-Speech API**. Detaily níže v [Požadavky](#požadavky)
> a [Setup klíče](#setup-klíče-jednorázově).

```text
# 1) Přidej tenhle repozitář jako marketplace
/plugin marketplace add revautec/voiceclaude

# 2) Nainstaluj plugin (při instalaci tě požádá o googleApiKey)
/plugin install voice-claude@voice-claude

# 3) Ověř, že vše sedí
/speak doctor
```

A je to — od téhle chvíle ti Claude po každé odpovědi **česky nahlas přečte
krátké shrnutí**. Vypnout/zapnout kdykoli přes `/speak off` a `/speak on`.

**Co se při instalaci stane (proč to rovnou mluví):**

1. `/plugin marketplace add` načte z repozitáře `.claude-plugin/marketplace.json` →
   Claude Code uvidí plugin `voice-claude`.
2. `/plugin install` přečte `.claude-plugin/plugin.json`: zaregistruje slash command
   `/speak`, oba hooky z `hooks/hooks.json` a zeptá se na hodnoty z `userConfig`
   (hlavně `googleApiKey`, který uloží do systémového keychainu). Hodnoty se
   skriptům předají jako `CLAUDE_PLUGIN_OPTION_*`.
3. Při startu každého sezení **SessionStart hook** (`injectvoiceinstruction.sh`)
   tiše řekne Claudovi, ať na konec běžných odpovědí přidává `<voice>…</voice>`.
4. Po dokončení každé odpovědi **Stop hook** (`speak.sh`) vytáhne obsah `<voice>`,
   pošle ho do Google TTS, dostane WAV a přehraje ho na pozadí.

Plugin je tak **mluvící hned po instalaci**, bez další konfigurace (default je
zapnuto). Pro vývoj/test bez marketplace lze i `claude --plugin-dir ./voiceclaude`.

## Jak to funguje

```
Claude dokončí odpověď → Stop hook (hooks/speak.sh)
  → scripts/resolve.py vytáhne <voice>…</voice>
  → scripts/tts.py (jen Python stdlib) → Cloud TTS → WAV
  → přehraje na pozadí (pw-play / aplay / ffplay / mpv)
```

Při startu sezení vloží `hooks/injectvoiceinstruction.sh` Claudovi instrukci, aby
na konec běžných odpovědí přidával `<voice>…</voice>` (a nepřidával ho do
strukturovaných / klientských výstupů).

Hlasový **vstup** (mluvit na Clauda) řeš vestavěným `/voice` v Claude Code — tenhle
plugin je jen **výstup**.

## Požadavky

- Claude Code s podporou pluginů (testováno na 2.1.161).
- **Python 3** (jen standardní knihovna — nic se nepipuje).
- **`jq`** (Stop hook jím parsuje stav a odpověď).
- Audio přehrávač: `pw-play` / `paplay` / `aplay` / `ffplay` / `mpv`.
- **Google API klíč** s přístupem k **Cloud Text-to-Speech API**.

## Setup klíče (jednorázově)

1. V [Google Cloud Console](https://console.cloud.google.com) zapni **Cloud Text-to-Speech API**
   (APIs & Services → Library).
2. Vytvoř **API key** (Credentials → Create credentials → API key).
3. Doporučeno: u klíče **API restrictions → omez na „Cloud Text-to-Speech API"**.
   Pokud máš na klíči i **IP restriction**, přidej IP svého stroje (nebo ji nedávej).

## Instalace

Přímo z GitHubu:

```
/plugin marketplace add revautec/voiceclaude
/plugin install voice-claude@voice-claude
```

Nebo z lokální kopie repozitáře:

```
/plugin marketplace add ~/projects/voiceclaude
/plugin install voice-claude@voice-claude
```

Při instalaci zadej `googleApiKey` (uloží se do systémového keychainu). Alternativně
nech prázdné a měj klíč v prostředí jako `GOOGLE_API_KEY`.

Po instalaci ověř funkčnost:

```
/speak doctor
```

## Ovládání: `/speak`

| Příkaz | Co dělá |
|---|---|
| `/speak` nebo `/speak status` | stav (zap/vyp, hlas, tempo, mute, poslední chyba) |
| `/speak on` / `/speak off` | zapne / okamžitě ztiší |
| `/speak mute <n>` | ztlumí dalších **n** tahů, pak se sám zapne |
| `/speak voice <jméno>` | změní hlas (např. `cs-CZ-Chirp3-HD-Aoede`) |
| `/speak rate <0.25–2.0>` | tempo řeči |
| `/speak doctor` | preflight: python, přehrávač, klíč, poslední chyba |

Default: **zapnuto**.

## Soukromí

Mluvené **shrnutí** odpovědi se posílá do Google (TTS). Pro citlivé / klientské
projekty hlas vypni (`/speak off`). Plugin běží lokálně, klíč se nikam neposílá
kromě hlavičky volání na Google.

## Stav / log

- Stav: `~/.config/voice-claude/state.json`
- Log: `~/.config/voice-claude/voice-claude.log`
- Dočasné audio: `$XDG_RUNTIME_DIR/voice-claude/`

## Struktura repozitáře

```
.claude-plugin/
  plugin.json        # manifest pluginu + userConfig (googleApiKey, hlas, tempo…)
  marketplace.json   # marketplace listing pro /plugin marketplace add
commands/
  speak.md           # slash command /speak
hooks/
  hooks.json         # registrace SessionStart + Stop hooků
  injectvoiceinstruction.sh  # SessionStart: vloží instrukci na <voice> tag
  speak.sh           # Stop: vytáhne <voice>, syntéza a přehrání
scripts/
  resolve.py         # extrakce <voice>…</voice>
  tts.py             # Google Cloud TTS (jen stdlib)
  state.py           # atomický stav v ~/.config/voice-claude/state.json
  speakctl.sh        # logika /speak
  doctor.sh          # diagnostika
  play.sh            # přehrávač audia
```

## Limity (MVP, fáze 1)

- Engine Cloud TTS Chirp HD přes API klíč (funguje v praxi; Google ho pro TTS
  oficiálně neuvádí — alternativa je service-account).
- `cs-CZ` Chirp HD nemá SSML/pauzy → pauzy řeší interpunkce + tempo.
- Plánováno dál: redakce tajemství, per-projekt denylist, streaming nízká latence,
  browser/mobil klienti (sdílené „Voice Core").
