#!/usr/bin/env python3
"""voice-claude — plovoucí mini-panel (always-on-top) pro ovládání myší.

Malé okno s tlačítky, které leží nad terminálem. Klikáš myší, změny se hned
ukládají do stejného ~/.config/voice-claude/state.json, který čte plugin —
panel, /speak i hlas jsou pořád synchronní (panel se sám aktualizuje).

Funkce: zap/vyp, MUTE (na pár tahů, na první klik), krátké/dlouhé, výběr hlasu,
tempo, přepínač vodorovně/svisle (⇅), automatický dark/light dle OS (◑) a
přepínání průhlednosti (100/75/50 %).

Funguje na Windows 11 (přes WSLg), Ubuntu i macOS. Jen Python stdlib (Tkinter).
  Ubuntu/WSL:  sudo apt install python3-tk
  macOS:       bývá součástí Pythonu (nebo: brew install python-tk)

Spuštění:   python3 panel.py        (nebo /speak panel)
"""
import os
import sys
import shutil
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state  # noqa: E402  (sdílený atomický stav)
import voices  # noqa: E402  (seznam hlasů)

try:
    import tkinter as tk
except Exception:
    sys.stderr.write(
        "Chybí Tkinter. Ubuntu/WSL: sudo apt install python3-tk | "
        "macOS: brew install python-tk\n"
    )
    sys.exit(1)

POLL_MS = 1000
RATE_STEP = 0.25
RATE_MIN, RATE_MAX = 0.25, 2.0
ALPHA_CYCLE = [1.0, 0.75, 0.5]
MUTE_CYCLE = [0, 1, 3, 999999]          # klik cykluje: vyp → 1 → 3 → ∞ → vyp
THEME_CYCLE = ["auto", "dark", "light"]

DARK = dict(bg="#1f1f23", sub="#26262b", fg="#e6e6e6", btn="#34343a",
            active="#45454d", on="#2e7d32", off="#a83a3a", mute="#9a6a12",
            white="#ffffff", handle="#3a3a42")
LIGHT = dict(bg="#ededed", sub="#e3e3e3", fg="#1b1b1b", btn="#dadada",
             active="#c4c4c4", on="#3f9442", off="#d84141", mute="#c79a2e",
             white="#ffffff", handle="#cfcfcf")


def detect_dark():
    """Best-effort detekce tmavého režimu OS (macOS / Windows / WSL / GNOME)."""
    env = os.environ.get("VC_PANEL_THEME", "").strip().lower()
    if env in ("dark", "light"):
        return env == "dark"
    try:
        if sys.platform == "darwin":
            r = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"],
                               capture_output=True, text=True, timeout=2)
            return "dark" in r.stdout.lower()
        if os.name == "nt":
            import winreg
            k = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
        # WSL: zeptej se Windows hosta
        if shutil.which("powershell.exe"):
            r = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 "(Get-ItemProperty -Path "
                 "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes"
                 "\\Personalize).AppsUseLightTheme"],
                capture_output=True, text=True, timeout=4)
            s = r.stdout.strip()
            if s in ("0", "1"):
                return s == "0"
        # GNOME / Linux
        if shutil.which("gsettings"):
            r = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=2)
            low = r.stdout.lower()
            if "dark" in low:
                return True
            if "light" in low:
                return False
            r2 = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                capture_output=True, text=True, timeout=2)
            if "dark" in r2.stdout.lower():
                return True
    except Exception:
        pass
    return True  # fallback: tmavý


def voice_catalog():
    out = []
    for label_g, names, g in (("žena", voices.FEMALE, "female"),
                              ("muž", voices.MALE, "male")):
        for n in names:
            out.append(("%s · %s" % (label_g, n), voices.PREFIX + n, g))
    return out


def _next(value, cycle):
    """Další prvek v cyklu (s tolerancí pro floaty); mimo cyklus → první."""
    for i, v in enumerate(cycle):
        if abs(v - value) < 1e-6 if isinstance(v, float) else v == value:
            return cycle[(i + 1) % len(cycle)]
    return cycle[0]


class Panel:
    def __init__(self, root):
        self.root = root
        self.catalog = voice_catalog()
        self.label_by_full = {full: lbl for lbl, full, _ in self.catalog}
        self.meta_by_label = {lbl: (full, g) for lbl, full, g in self.catalog}
        self._syncing = False
        self.borderless = sys.platform != "darwin"  # mac: nech nativní titlebar

        fam = {"darwin": "Helvetica Neue", "win32": "Segoe UI"}.get(
            sys.platform, "DejaVu Sans")
        self.font = (fam, 10)
        self.font_b = (fam, 10, "bold")

        root.title("voice")
        root.attributes("-topmost", True)
        root.resizable(False, False)
        if self.borderless:
            root.overrideredirect(True)
        try:
            root.geometry("+120+120")
        except Exception:
            pass

        self.snd = tk.StringVar()
        self.mute = tk.StringVar()
        self.length = tk.StringVar()
        self.rate = tk.StringVar()
        self.voice = tk.StringVar()
        self.alpha_lbl = tk.StringVar()

        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True)

        s = self._read()
        self.orientation = s.get("panelOrientation") or "h"
        self.theme_mode = s.get("panelTheme") or "auto"
        self.alpha = self._coerce_alpha(s.get("panelAlpha"))
        self.recompute_theme()
        self.apply_window()
        self.build()
        self.sync()

    # ---- stav --------------------------------------------------------------
    def _read(self):
        return state.load()

    def _write(self, **kw):
        s = state.load()
        s.update(kw)
        state.save(s)
        self.sync_now()

    @staticmethod
    def _coerce_alpha(v):
        try:
            a = float(v)
            return a if 0.2 <= a <= 1.0 else 1.0
        except (TypeError, ValueError):
            return 1.0

    # ---- vzhled ------------------------------------------------------------
    def recompute_theme(self):
        dark = detect_dark() if self.theme_mode == "auto" else self.theme_mode == "dark"
        self.c = DARK if dark else LIGHT

    def apply_window(self):
        self.root.configure(bg=self.c["bg"])
        try:
            self.root.attributes("-alpha", self.alpha)
        except Exception:
            pass
        self.alpha_lbl.set("%d%%" % int(round(self.alpha * 100)))

    def _btn(self, parent, cmd, var=None, text=None, width=None, bold=False):
        b = tk.Button(parent, command=cmd, relief="flat", bd=0,
                      padx=8, pady=5, cursor="hand2", highlightthickness=0,
                      font=self.font_b if bold else self.font,
                      bg=self.c["btn"], fg=self.c["fg"],
                      activebackground=self.c["active"],
                      activeforeground=self.c["fg"])
        if var is not None:
            b.config(textvariable=var)
        else:
            b.config(text=text)
        if width:
            b.config(width=width)
        return b

    def build(self):
        for w in self.container.winfo_children():
            w.destroy()
        self.container.configure(bg=self.c["bg"])

        vert = self.orientation == "v"
        side = "top" if vert else "left"
        pack = {"fill": "x"} if vert else {"fill": "y"}
        pad = {"padx": 2, "pady": 2}

        def add(w):
            w.pack(side=side, **pack, **pad)

        # úchyt pro tažení (jen bezrámové okno)
        if self.borderless:
            h = tk.Label(self.container, text="≡", bg=self.c["handle"],
                         fg=self.c["fg"], font=self.font, cursor="fleur",
                         padx=4, pady=4)
            h.bind("<Button-1>", self._start_move)
            h.bind("<B1-Motion>", self._do_move)
            add(h)

        self.b_power = self._btn(self.container, self.toggle_sound,
                                 var=self.snd, width=6, bold=True)
        add(self.b_power)

        self.b_mute = self._btn(self.container, self.cycle_mute,
                                var=self.mute, width=8, bold=True)
        add(self.b_mute)

        self.b_len = self._btn(self.container, self.toggle_length,
                               var=self.length, width=8)
        add(self.b_len)

        labels = [lbl for lbl, _, _ in self.catalog]
        om = tk.OptionMenu(self.container, self.voice, *labels,
                           command=self.pick_voice)
        om.config(width=12, relief="flat", bd=0, highlightthickness=0,
                  font=self.font, bg=self.c["btn"], fg=self.c["fg"],
                  activebackground=self.c["active"],
                  activeforeground=self.c["fg"],
                  indicatoron=True, cursor="hand2")
        om["menu"].config(bg=self.c["sub"], fg=self.c["fg"],
                          activebackground=self.c["active"],
                          activeforeground=self.c["fg"], bd=0)
        self.b_voice = om
        add(om)

        rate_box = tk.Frame(self.container, bg=self.c["bg"])
        self._btn(rate_box, lambda: self.bump_rate(-RATE_STEP),
                  text="−", width=2).pack(side="left", padx=1)
        tk.Label(rate_box, textvariable=self.rate, width=4, anchor="center",
                 bg=self.c["sub"], fg=self.c["fg"], font=self.font,
                 padx=2, pady=4).pack(side="left", padx=1)
        self._btn(rate_box, lambda: self.bump_rate(+RATE_STEP),
                  text="+", width=2).pack(side="left", padx=1)
        add(rate_box)

        self.b_theme = self._btn(self.container, self.cycle_theme,
                                 text="◑", width=2)
        add(self.b_theme)

        self.b_alpha = self._btn(self.container, self.cycle_alpha,
                                 var=self.alpha_lbl, width=5)
        add(self.b_alpha)

        self.b_orient = self._btn(self.container, self.toggle_orientation,
                                  text="⇅", width=2)
        add(self.b_orient)

        if self.borderless:
            self._btn(self.container, self.root.destroy,
                      text="×", width=2).pack(side=side, **pack, **pad)

    # ---- tažení okna -------------------------------------------------------
    def _start_move(self, e):
        self._ox, self._oy = e.x, e.y

    def _do_move(self, e):
        self.root.geometry("+%d+%d" % (e.x_root - self._ox, e.y_root - self._oy))

    # ---- akce --------------------------------------------------------------
    def toggle_sound(self):
        if self._read().get("enabled"):
            self._write(enabled=False)
        else:
            self._write(enabled=True, muteRemaining=0)

    def cycle_mute(self):
        cur = int(self._read().get("muteRemaining") or 0)
        self._write(muteRemaining=_next(cur, MUTE_CYCLE))

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
        try:
            cur = float(self._read().get("speakingRate") or 1.0)
        except (TypeError, ValueError):
            cur = 1.0
        new = min(RATE_MAX, max(RATE_MIN, cur + delta))
        new = round(new / RATE_STEP) * RATE_STEP
        self._write(speakingRate=round(new, 2))

    def cycle_theme(self):
        self.theme_mode = _next(self.theme_mode, THEME_CYCLE)
        self._write(panelTheme=self.theme_mode)
        self.recompute_theme()
        self.apply_window()
        self.build()
        self.sync_now()

    def cycle_alpha(self):
        self.alpha = _next(self.alpha, ALPHA_CYCLE)
        self._write(panelAlpha=self.alpha)
        self.apply_window()

    def toggle_orientation(self):
        self.orientation = "v" if self.orientation == "h" else "h"
        self._write(panelOrientation=self.orientation)
        self.build()
        self.sync_now()

    # ---- synchronizace -----------------------------------------------------
    def sync_now(self):
        s = self._read()
        self._syncing = True
        try:
            on = bool(s.get("enabled"))
            self.snd.set("● ZAP" if on else "● VYP")
            self.b_power.config(bg=self.c["on"] if on else self.c["off"],
                                fg=self.c["white"],
                                activebackground=self.c["on"] if on else self.c["off"],
                                activeforeground=self.c["white"])

            m = int(s.get("muteRemaining") or 0)
            if m <= 0:
                self.mute.set("TICHO")
                self.b_mute.config(bg=self.c["btn"], fg=self.c["fg"],
                                   activebackground=self.c["active"],
                                   activeforeground=self.c["fg"])
            else:
                self.mute.set("TICHO ∞" if m >= 100000 else "TICHO %d" % m)
                self.b_mute.config(bg=self.c["mute"], fg=self.c["white"],
                                   activebackground=self.c["mute"],
                                   activeforeground=self.c["white"])

            short = (s.get("summaryLength") or "long") == "short"
            self.length.set("KRÁTKÉ" if short else "DLOUHÉ")

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
