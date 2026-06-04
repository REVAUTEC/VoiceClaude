# voice-claude

Claude Code plugin, který **nahlas předčítá mluvené shrnutí** každé odpovědi Claude
přes **Google Cloud Text-to-Speech (Chirp 3 HD)** — primárně **česky**, hlas
`cs-CZ-Chirp3-HD-Achernar`.

Shrnutí píše sám Claude do tagu `<voice>…</voice>` na konci odpovědi (žádný druhý
LLM krok → nulová extra latence). Plugin přečte jen obsah tagu. Čte se **až po
úplném dokončení** odpovědi (Stop hook), nikdy během psaní.

## ⚡ Instalace ve 3 krocích

> Potřebuješ Claude Code, `python3`, `jq`, audio přehrávač a Google API klíč
> s povoleným **Cloud Text-to-Speech API**. Detaily v [Požadavky](#požadavky)
> a [Setup klíče](#setup-klíče-jednorázově).

**1. Přidej marketplace** (HTTPS – funguje bez SSH klíče):
```text
/plugin marketplace add https://github.com/revautec/voiceclaude.git
```

**2. Nainstaluj plugin** (při instalaci tě požádá o `googleApiKey`):
```text
/plugin install voice-claude@voice-claude
```

**3. Ověř, že vše sedí:**
```text
/voice-claude:speak doctor
```

A je to — od téhle chvíle ti Claude po každé odpovědi **česky nahlas přečte
krátké shrnutí**.

> **📛 Jak se volají příkazy:** u pluginů jsou příkazy **jmenné (namespaced)** — píšeš
> vždy **celé `/voice-claude:speak …`** (zkrácené `speak` bez prefixu Claude Code
> nenabídne). V našeptávači (`/`) stačí napsat `voice` nebo `speak` a vybrat ze
> seznamu. Nejčastější:
> ```text
> /voice-claude:speak            # stav
> /voice-claude:speak off        # vypnout   ( … on = zapnout )
> /voice-claude:speak panel      # plovoucí ovládací panel (klikání myší)
> /voice-claude:speak doctor     # diagnostika
> ```

> **⚠️ Proč HTTPS URL a ne zkratka `revautec/voiceclaude`:** Claude Code u zkratky
> `owner/repo` klonuje přes SSH (`git@github.com`) → na stroji bez GitHub SSH klíče to
> selže i u veřejného repa. Použij **plnou HTTPS adresu s `.git`** (jako v kroku 1),
> nebo `export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`. Víc v
> [Řešení potíží](#řešení-potíží-instalace).

**Co se při instalaci stane (proč to rovnou mluví):**

1. `/plugin marketplace add` načte z repozitáře `.claude-plugin/marketplace.json` →
   Claude Code uvidí plugin `voice-claude`.
2. `/plugin install` přečte `.claude-plugin/plugin.json`: zaregistruje slash command
   (v našeptávači jako **`/voice-claude:speak`**), oba hooky z `hooks/hooks.json`
   a zeptá se na hodnoty z `userConfig`
   (hlavně `googleApiKey`, který uloží do systémového keychainu). Hodnoty se
   skriptům předají jako `CLAUDE_PLUGIN_OPTION_*`.
3. Při startu každého sezení **SessionStart hook** (`injectvoiceinstruction.sh`)
   tiše řekne Claudovi, ať na konec běžných odpovědí přidává `<voice>…</voice>`.
4. Po dokončení každé odpovědi **Stop hook** (`speak.sh`) vytáhne obsah `<voice>`,
   pošle ho do Google TTS, dostane WAV a přehraje ho na pozadí.

Plugin je tak **mluvící hned po instalaci**, bez další konfigurace (default je
zapnuto). Pro vývoj/test bez marketplace lze i `claude --plugin-dir ./voiceclaude`.

## 🎛️ Ovládací panel (klikání myší)

Nemusíš nic psát — spusť **ovládací panel** a klikej myší:

```text
/voice-claude:speak panel
```

![voice-claude — ovládací panel](docs/panel-dark.png)

Plovoucí ikonová lišta leží **nad terminálem** (always-on-top) a každý klik se hned
uloží do stavu, který plugin čte — panel, příkazy i hlas jsou pořád synchronní. Ikony
jsou vlastní vektorové, hladké (anti-aliasované) přes volitelný **Pillow**. Co která
ikona dělá, instalaci a držení nad Warpem najdeš v sekci
[Plovoucí panel](#plovoucí-panel-ovládání-myší) níže.

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

Pro **mluvení** (jádro pluginu):

- Claude Code s podporou pluginů (testováno na 2.1.161).
- **Python 3** (jádro jede jen na standardní knihovně — nic se nepipuje).
- **`jq`** (Stop hook jím parsuje stav a odpověď).
- Audio přehrávač: `pw-play` / `paplay` / `aplay` / `ffplay` / `mpv` (ve WSLg je nejčistší `paplay` z `pulseaudio-utils`).
- **Google API klíč** s přístupem k **Cloud Text-to-Speech API**.

Pro **plovoucí panel** (volitelné, viz [Plovoucí panel](#plovoucí-panel-ovládání-myší)):

- **Ubuntu/Linux:** `python3-tk` (+ volitelně `python3-pil` pro hladké ikony).
- **macOS:** Tkinter v Pythonu (+ volitelně Pillow).
- **Windows + WSL:** **Python pro Windows** (panel běží nativně kvůli always-on-top).

Vše pro panel ti zkontroluje `/voice-claude:speak doctor`.

## Setup klíče (jednorázově)

1. V [Google Cloud Console](https://console.cloud.google.com) zapni **Cloud Text-to-Speech API**
   (APIs & Services → Library).
2. Vytvoř **API key** (Credentials → Create credentials → API key).
3. Doporučeno: u klíče **API restrictions → omez na „Cloud Text-to-Speech API"**.
   Pokud máš na klíči i **IP restriction**, přidej IP svého stroje (nebo ji nedávej).

## Instalace

Přímo z GitHubu (HTTPS – doporučeno, funguje bez SSH klíče):

```
/plugin marketplace add https://github.com/revautec/voiceclaude.git
/plugin install voice-claude@voice-claude
```

Nebo z lokální kopie / rozbaleného ZIPu (úplně bez gitu):

```
/plugin marketplace add ~/voiceclaude-main
/plugin install voice-claude@voice-claude
```

Při instalaci zadej `googleApiKey` (uloží se do systémového keychainu). Alternativně
nech prázdné a měj klíč v prostředí jako `GOOGLE_API_KEY`.

Po instalaci ověř funkčnost:

```text
/voice-claude:speak doctor
```

## Řešení potíží (instalace)

**`SSH authentication failed … git@github.com: Permission denied (publickey)`**

Claude Code u zkratky `owner/repo` klonuje přes SSH; bez GitHub SSH klíče to selže
i u veřejného repa. Vyber si jedno řešení:

1. **Použij HTTPS URL** (nejjednodušší):
   ```
   /plugin marketplace add https://github.com/revautec/voiceclaude.git
   ```
2. **Povol HTTPS pro zkratky** přes proměnnou prostředí (Claude Code v2.1.141+):
   ```bash
   export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1
   ```
3. **Instalace ze ZIPu – úplně bez gitu** (funguje vždycky):
   stáhni
   [main.zip](https://github.com/revautec/voiceclaude/archive/refs/heads/main.zip),
   rozbal a přidej rozbalenou složku jako lokální marketplace:
   ```
   /plugin marketplace add ~/voiceclaude-main
   /plugin install voice-claude@voice-claude
   ```

**I HTTPS končí SSH chybou?** Tvůj git má globální přepis adres. Ověř a zruš:
```bash
git config --show-origin --get-regexp 'url.*insteadof'      # ukáže pravidlo
git config --global --unset-all url."git@github.com:".insteadOf
```
…nebo prostě použij ZIP variantu (bod 3), která git vůbec nepoužívá.

## Ovládání: `/voice-claude:speak`

> **Pozn. k názvu:** Claude Code u pluginů používá **jmenné (namespaced) příkazy** —
> píšeš vždy celé **`/voice-claude:speak …`**. V našeptávači (`/`) stačí napsat
> `voice` nebo `speak` a vybrat ho ze seznamu.

| Příkaz | Co dělá |
|---|---|
| `/voice-claude:speak` nebo `/voice-claude:speak status` | stav (zap/vyp, délka, pohlaví, hlas, tempo, mute, poslední chyba) |
| `/voice-claude:speak on` / `/voice-claude:speak off` / `/voice-claude:speak toggle` | zapne / vypne / přepne |
| `/voice-claude:speak short` / `/voice-claude:speak long` / `/voice-claude:speak length` | délka shrnutí: **krátké** (jen 1. věta) / **dlouhé** (celé `<voice>`) / přepnout |
| `/voice-claude:speak mute <n>` | ztlumí dalších **n** tahů, pak se sám zapne |
| `/voice-claude:speak gender <žena\|muž>` | vybere pohlaví a tím výchozí hlas (žena → Aoede, muž → Charon) |
| `/voice-claude:speak voices` | vypíše dostupné české Chirp 3 HD hlasy |
| `/voice-claude:speak voice <jméno>` | konkrétní hlas krátkým jménem (např. `/voice-claude:speak voice Leda`) |
| `/voice-claude:speak rate <0.25–2.0>` | tempo řeči |
| `/voice-claude:speak panel` | spustí **plovoucí ovládací panel** (viz níže) |
| `/voice-claude:speak doctor` | preflight: python, jq, přehrávač, klíč, poslední chyba |

Default: **zapnuto**, jazyk **cs-CZ** (napevno), hlas **ženský** (Aoede), délka **dlouhé**,
max. délka **1500** znaků.

## Plovoucí panel (ovládání myší)

Když nechceš psát příkazy, spusť **mini-appku** — kompaktní **ikonovou lištu**, která
**leží nad terminálem (always-on-top)** a ovládáš ji **myší**. Ikony jsou vlastní
vektorové (Material styl, kreslené na canvasu) — **bez závislostí navíc**, jen Tkinter.
Klik se hned uloží do stejného stavu, který čte plugin, takže panel, `/voice-claude:speak` i hlas
jsou pořád synchronní (panel se sám aktualizuje ~1×/s). Popisek každé ikony se ukáže
jako **tooltip** při najetí myší.

Ikony zleva doprava:

| Ikona | Co dělá |
|---|---|
| ⠿ | úchyt — táhni pro přesun okna |
| ⏻ | **zvuk** zap/vyp (zelená = zapnuto, červená = vypnuto) |
| 🔇 | **ztlumit** na první klik: **1 → 3 → ∞ tahů → vyp** (jantarová + počet), pak se sám zapne |
| ☰ | **délka** shrnutí: krátké ↔ dlouhé |
| 👤 | **hlas** — klik otevře nabídku českých Chirp 3 HD hlasů |
| ◔ | **tempo** — klik cykluje (0.75–2×), kolečko myši jemně ±0.25 |
| ◑ | **téma** — auto (dle OS) → tmavé → světlé (automatický dark mode) |
| ▣ | **průhlednost** — 100 → 75 → 50 % |
| ⇅ | **orientace** — vodorovně ↔ svisle |
| 📌 | **vždy navrchu** zap/vyp (špendlík: plný = zapnuto, obrys = vypnuto) |
| ✕ | zavřít (bezrámové okno; na macOS nativní lišta) |

Vzhled se ukládá do stavu (`panelTheme`, `panelAlpha`, `panelOrientation`), takže se
panel otevře tak, jak jsi ho nechal.

Světlý motiv (auto dle OS) a svislá orientace (přepínač ⇅):

<p align="left">
  <img src="docs/panel-light.png" alt="voice-claude panel — světlý motiv" width="540">
  &nbsp;
  <img src="docs/panel-vertical.png" alt="voice-claude panel — svislá orientace" height="190">
</p>

**Spuštění:** `/voice-claude:speak panel` (doporučeno — spouštěč si vyřeší správný Python i cesty
sám). `/voice-claude:speak doctor` zkontroluje, že máš pro panel vše potřebné.

**Co doinstalovat (podle platformy):**

| Platforma | Panel běží | Instalace |
|---|---|---|
| **Ubuntu / Linux** | lokální Python | `sudo apt install python3-tk python3-pil` |
| **macOS** | lokální Python | Tkinter bývá v Pythonu (jinak `brew install python-tk`); ikony: `pip install pillow` |
| **Windows + WSL** | **nativní Windows Python** (kvůli always-on-top, viz níže) | nainstaluj **Python pro Windows** (python.org / Microsoft Store); ikony: `python.exe -m pip install pillow` |

**Hladké ikony (volitelné):** s **Pillow** se ikony vykreslí anti-aliasovaně
(supersampling). Bez Pillow se použijí jednodušší vektorové ikony kreslené přímo na
canvasu — panel funguje i tak.

**Always-on-top ve Windows/WSL:** WSLg okno (Linux GUI přes RAIL) **neumí držet
topmost nad nativními Windows okny** (Warp, Windows Terminal…) — z Linux strany se to
spolehlivě nevyřeší. Proto ve WSL `/voice-claude:speak panel` spustí panel **nativně ve Windows
Pythonem** (`python.exe`), kde `-topmost` je standardní Win32 a **drží nad Warpem**.
Panel přitom sahá do **stejného** `state.json` ve WSL přes `\\wsl.localhost\…` cestu,
takže zůstává synchronní s pluginem.

- **Podmínka:** mít na Windows nainstalovaný **Python** (python.org nebo Microsoft
  Store). Ověř v WSL: `python.exe --version`. Tkinter je součástí; pro hladké ikony
  volitelně `python.exe -m pip install pillow`.
- Na **Ubuntu/macOS** topmost funguje nativně přes Tkinter, žádný Windows Python netřeba.
- Ruční spuštění nativního panelu z WSL:
  `python.exe "$(wslpath -w .../scripts/panel.py)" "$(wslpath -w ~/.config/voice-claude/state.json)"`
- Špendlík v panelu přepíná „vždy navrchu" zap/vyp.

### Výběr hlasu

Plugin používá **jen české Chirp 3 HD hlasy**. Nemusíš psát celý název — buď zvol
pohlaví (`/voice-claude:speak gender žena|muž`), nebo krátké jméno (`/voice-claude:speak voice Aoede`):

- **ženské:** Aoede, Kore, Leda, Zephyr
- **mužské:** Puck, Charon, Fenrir, Orus

Pohlaví lze předvybrat i při instalaci v poli **„Hlas: žena nebo muž"**.

> Pozn.: Claude Code v instalačním dialogu neumí rozbalovací/radio výběr — proto je
> pohlaví textové pole a konkrétní jméno hlasu se volí příkazem `/voice-claude:speak voice`.

## Kvalita zvuku

Pokud řeč **šumí** nebo zní méně kvalitně, je to skoro vždy v **přehrávání**, ne v TTS
(audio z Googlu je bezztrátové LINEAR16):

- **Nainstaluj nativní přehrávač.** `play.sh` preferuje `pw-play` → `paplay` → `aplay`
  → `ffplay` → `mpv`. `ffplay` na PipeWire systémech často převzorkovává nečistě.
  Čistší bývá PipeWire/PulseAudio:
  ```bash
  sudo apt install pipewire-bin      # → pw-play
  # nebo:
  sudo apt install pulseaudio-utils  # → paplay
  ```
  Po instalaci je `/voice-claude:speak doctor` ukáže jako vybraný přehrávač.
- **Vzorkovací frekvence:** plugin si o zvuk říká ve **48 kHz** (čisté převzorkování na
  straně Googlu), což omezuje šum z lokálního převzorkování. Lze změnit přes
  `export VC_SAMPLE_RATE=24000` (nativní rychlost Chirp 3 HD).

## Soukromí

Mluvené **shrnutí** odpovědi se posílá do Google (TTS). Pro citlivé / klientské
projekty hlas vypni (`/voice-claude:speak off`). Plugin běží lokálně, klíč se nikam neposílá
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
  speak.md           # slash command /voice-claude:speak
hooks/
  hooks.json         # registrace SessionStart + Stop hooků
  injectvoiceinstruction.sh  # SessionStart: vloží instrukci na <voice> tag
  speak.sh           # Stop: vytáhne <voice>, syntéza a přehrání
scripts/
  resolve.py         # extrakce <voice>…</voice>
  tts.py             # Google Cloud TTS (jen stdlib)
  state.py           # atomický stav v ~/.config/voice-claude/state.json
  voices.py          # české Chirp 3 HD hlasy + mapování pohlaví → jméno
  panel.py           # plovoucí ikonový panel (Tkinter; AA ikony přes volitelný
                     #   Pillow; dark/light, průhlednost, H/V, always-on-top)
  speakctl.sh        # logika /voice-claude:speak (vč. spuštění panelu — ve WSL Windows Pythonem)
  doctor.sh          # diagnostika
  play.sh            # přehrávač audia
```

## Limity (MVP, fáze 1)

- Engine Cloud TTS Chirp HD přes API klíč (funguje v praxi; Google ho pro TTS
  oficiálně neuvádí — alternativa je service-account).
- `cs-CZ` Chirp HD nemá SSML/pauzy → pauzy řeší interpunkce + tempo.
- Plánováno dál: redakce tajemství, per-projekt denylist, streaming nízká latence,
  browser/mobil klienti (sdílené „Voice Core").
