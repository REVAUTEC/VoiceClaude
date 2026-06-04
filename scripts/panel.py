#!/usr/bin/env python3
"""voice-claude — plovoucí mini-panel (always-on-top) pro ovládání myší.

Malé okno s tlačítky, které leží nad terminálem. Klikáš myší, změny se hned
ukládají do stejného ~/.config/voice-claude/state.json, který čte plugin —
takže panel, /speak i hlas jsou pořád synchronní (panel se sám aktualizuje).

Funguje na Windows 11 (přes WSLg), Ubuntu i macOS. Jen Python stdlib (Tkinter).
  Ubuntu/WSL:  sudo apt install python3-tk
  macOS:       bývá součástí Pythonu (nebo: brew install python-tk)

Spuštění:   python3 panel.py        (nebo /speak panel)
Přepínač orientace (vodorovně/svisle) je tlačítko ⇅ přímo v panelu.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state  # noqa: E402  (sdílený atomický stav)
import voices  # noqa: E402  (seznam hlasů)

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    sys.stderr.write(
        "Chybí Tkinter. Ubuntu/WSL: sudo apt install python3-tk | "
        "macOS: brew install python-tk\n"
    )
    sys.exit(1)

POLL_MS = 1000           # jak často se panel sesynchronizuje se state.json
RATE_STEP = 0.25
RATE_MIN, RATE_MAX = 0.25, 2.0


def voice_catalog():
    """[(label, full_voice, gender), ...] pro všechny nabízené hlasy."""
    out = []
    for label_g, names, g in (("žena", voices.FEMALE, "female"),
                              ("muž", voices.MALE, "male")):
        for n in names:
            out.append(("%s · %s" % (label_g, n), voices.PREFIX + n, g))
    return out


class Panel:
    def __init__(self, root):
        self.root = root
        self.catalog = voice_catalog()
        self.label_by_full = {full: lbl for lbl, full, _ in self.catalog}
        self.meta_by_label = {lbl: (full, g) for lbl, full, g in self.catalog}
        self._syncing = False

        root.title("voice")
        root.attributes("-topmost", True)
        root.resizable(False, False)
        try:
            root.geometry("+120+120")
        except Exception:
            pass

        # Tkinter proměnné svázané s tlačítky (přežijí přestavbu layoutu).
        self.snd = tk.StringVar()
        self.length = tk.StringVar()
        self.rate = tk.StringVar()
        self.voice = tk.StringVar()

        self.container = ttk.Frame(root, padding=4)
        self.container.pack(fill="both", expand=True)

        self.orientation = self._read().get("panelOrientation") or "h"
        self.build()
        self.sync()  # první naplnění + nastartuje smyčku

    # ---- stav --------------------------------------------------------------
    def _read(self):
        return state.load()

    def _write(self, **kw):
        s = state.load()
        s.update(kw)
        state.save(s)
        self.sync_now()

    # ---- layout ------------------------------------------------------------
    def build(self):
        for w in self.container.winfo_children():
            w.destroy()

        vert = self.orientation == "v"
        side = "top" if vert else "left"
        pad = {"padx": 2, "pady": 2} if vert else {"padx": 2, "pady": 0}
        fill = "x" if vert else "y"

        def add(w):
            w.pack(side=side, fill=fill, **pad)

        self.b_snd = ttk.Button(self.container, textvariable=self.snd,
                                width=9, command=self.toggle_sound)
        add(self.b_snd)

        self.b_len = ttk.Button(self.container, textvariable=self.length,
                                width=10, command=self.toggle_length)
        add(self.b_len)

        labels = [lbl for lbl, _, _ in self.catalog]
        self.b_voice = ttk.OptionMenu(self.container, self.voice,
                                      self.voice.get() or labels[0],
                                      *labels, command=self.pick_voice)
        self.b_voice.configure(width=12)
        add(self.b_voice)

        # tempo: −  [1.0]  +
        rate_box = ttk.Frame(self.container)
        ttk.Button(rate_box, text="−", width=2,
                   command=lambda: self.bump_rate(-RATE_STEP)).pack(side="left")
        ttk.Label(rate_box, textvariable=self.rate, width=6,
                  anchor="center").pack(side="left")
        ttk.Button(rate_box, text="+", width=2,
                   command=lambda: self.bump_rate(+RATE_STEP)).pack(side="left")
        add(rate_box)

        self.b_orient = ttk.Button(self.container, text="⇅", width=3,
                                   command=self.toggle_orientation)
        add(self.b_orient)

    # ---- akce (klik) -------------------------------------------------------
    def toggle_sound(self):
        if self._read().get("enabled"):
            self._write(enabled=False)
        else:
            self._write(enabled=True, muteRemaining=0)

    def toggle_length(self):
        cur = self._read().get("summaryLength") or "long"
        self._write(summaryLength="short" if cur == "long" else "long")

    def pick_voice(self, label):
        if self._syncing:
            return
        full, gender = self.meta_by_label.get(label, (None, None))
        if full:
            self._write(voiceName=full, gender=gender)

    def bump_rate(self, delta):
        cur = self._rate_value()
        new = round(min(RATE_MAX, max(RATE_MIN, cur + delta)) / RATE_STEP) * RATE_STEP
        self._write(speakingRate=round(new, 2))

    def toggle_orientation(self):
        self.orientation = "v" if self.orientation == "h" else "h"
        self._write(panelOrientation=self.orientation)
        self.build()
        self.sync_now()

    # ---- synchronizace -----------------------------------------------------
    def _rate_value(self):
        try:
            r = float(self._read().get("speakingRate") or 1.0)
        except (TypeError, ValueError):
            r = 1.0
        return r

    def sync_now(self):
        s = self._read()
        self._syncing = True
        try:
            on = bool(s.get("enabled"))
            self.snd.set("🔊 ZAP" if on else "🔇 VYP")

            short = (s.get("summaryLength") or "long") == "short"
            self.length.set("✍ KRÁTKÉ" if short else "✍ DLOUHÉ")

            try:
                r = float(s.get("speakingRate") or 1.0)
            except (TypeError, ValueError):
                r = 1.0
            self.rate.set("%g×" % round(r, 2))

            full = s.get("voiceName") or voices.voice_for_gender(s.get("gender") or "")
            lbl = self.label_by_full.get(full)
            if lbl and lbl != self.voice.get():
                self.voice.set(lbl)
        finally:
            self._syncing = False

    def sync(self):
        self.sync_now()
        self.root.after(POLL_MS, self.sync)


def main():
    try:
        root = tk.Tk()
    except tk.TclError as e:
        sys.stderr.write(
            "Nepodařilo se otevřít okno (%s).\n"
            "Na WSL potřebuješ Windows 11 s WSLg (grafika ve WSL2).\n" % e
        )
        sys.exit(1)
    Panel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
