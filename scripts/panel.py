#!/usr/bin/env python3
"""voice-claude — plovoucí ikonový mini-panel (always-on-top).

Kompaktní lišta s vlastními vektorovými ikonami (Material styl) kreslenými na
Tkinter canvasu — bez jakýchkoli závislostí (jen stdlib). Klikáš myší, změny se
hned ukládají do ~/.config/voice-claude/state.json, který čte plugin; panel se
sám aktualizuje (~1×/s), takže panel, /speak i hlas jsou pořád synchronní.

Ikony (popisek = tooltip při najetí):
  ⏻ zvuk zap/vyp · 🔇 ztlumit (1→3→∞ tahů) · ☰ délka krátké/dlouhé ·
  👤 výběr hlasu · ◔ tempo · ◑ téma (auto/dark/light) · ▣ průhlednost ·
  ⇅ orientace · (⠿ táhnout, ✕ zavřít — bezrámové okno)

Win 11 (WSLg), Ubuntu, macOS. Potřebuje Tkinter:
  Ubuntu/WSL:  sudo apt install python3-tk
  macOS:       brew install python-tk
"""
import os
import sys
import shutil
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state  # noqa: E402
import voices  # noqa: E402

try:
    import tkinter as tk
except Exception:
    sys.stderr.write("Chybí Tkinter. Ubuntu/WSL: sudo apt install python3-tk\n")
    sys.exit(1)

# Volitelné: Pillow → anti-aliasované (hladké) ikony. Bez něj se použije
# vektorové kreslení na canvasu (funkční, jen méně hladké).
try:
    import io
    import base64
    from PIL import Image, ImageDraw
    HAS_PIL = True
except Exception:
    HAS_PIL = False

POLL_MS = 1000
RATE_STEP = 0.25
RATE_MIN, RATE_MAX = 0.25, 2.0
RATE_CYCLE = [0.75, 1.0, 1.25, 1.5, 2.0]
ALPHA_CYCLE = [1.0, 0.75, 0.5]
MUTE_CYCLE = [0, 1, 3, 999999]
THEME_CYCLE = ["auto", "dark", "light"]

CELL = 38
GAP = 3
MARGIN = 7
RAD = 10

DARK = dict(surface="#1b1b21", elevate="#2e2e38", fg="#d8d8df", dim="#71717c",
            on="#4cb050", off="#ef5350", amber="#ffb02e", accent="#6b9bff",
            menu_bg="#26262e", menu_fg="#e6e6ea", menu_act="#39394a")
LIGHT = dict(surface="#f4f4f7", elevate="#e4e4ec", fg="#3a3a44", dim="#a2a2ad",
             on="#43a047", off="#e53935", amber="#e8930a", accent="#3b6fe0",
             menu_bg="#ffffff", menu_fg="#23232b", menu_act="#e8eefc")


def detect_dark():
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
        if shutil.which("powershell.exe"):
            r = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 "(Get-ItemProperty -Path HKCU:\\Software\\Microsoft\\Windows"
                 "\\CurrentVersion\\Themes\\Personalize).AppsUseLightTheme"],
                capture_output=True, text=True, timeout=4)
            s = r.stdout.strip()
            if s in ("0", "1"):
                return s == "0"
        if shutil.which("gsettings"):
            r = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=2)
            low = r.stdout.lower()
            if "dark" in low:
                return True
            if "light" in low:
                return False
    except Exception:
        pass
    return True


def voice_catalog():
    out = []
    for g_lbl, names, g in (("žena", voices.FEMALE, "female"),
                            ("muž", voices.MALE, "male")):
        for n in names:
            out.append(("%s · %s" % (g_lbl, n), voices.PREFIX + n, g))
    return out


def _next(value, cycle):
    for i, v in enumerate(cycle):
        same = abs(v - value) < 1e-6 if isinstance(v, float) else v == value
        if same:
            return cycle[(i + 1) % len(cycle)]
    return cycle[0]


def render_icon(name, px, primary, accent, mode="auto", fill=1.0):
    """Vykreslí ikonu anti-aliasovaně (supersampling 4× + LANCZOS) → PIL Image.
    Souřadnice v „38-mřížce" se středem (0,0); P() je převede na pixely."""
    ss = 4
    d_px = px * ss
    s = d_px / 38.0
    img = Image.new("RGBA", (d_px, d_px), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cen = d_px / 2.0
    lw = max(1, int(round(2 * s)))
    tw = max(1, int(round(1 * s)))

    def P(ox, oy):
        return (cen + ox * s, cen + oy * s)

    def box(x1, y1, x2, y2):
        return [cen + x1 * s, cen + y1 * s, cen + x2 * s, cen + y2 * s]

    if name == "power":
        dr.arc(box(-9, -9, 9, 9), 300, 240, fill=primary, width=lw)
        dr.line([P(0, -11), P(0, -1)], fill=primary, width=lw)
    elif name == "mute":
        dr.polygon([P(-8, -3), P(-3, -3), P(1, -8), P(1, 8), P(-3, 3),
                    P(-8, 3)], fill=primary)
        if mode == "active":
            dr.line([P(-9, 9), P(9, -9)], fill=primary, width=lw)
        else:
            dr.arc(box(-2, -4, 6, 4), -55, 55, fill=primary, width=tw)
            dr.arc(box(-6, -8, 10, 8), -55, 55, fill=primary, width=tw)
    elif name == "length":
        rows = [(-3, 8), (3, 4)] if mode == "short" else [(-8, 9), (-3, 9),
                                                           (2, 7), (7, 5)]
        for dy, w in rows:
            dr.line([P(-8, dy), P(-8 + w + 6, dy)], fill=primary, width=lw)
    elif name == "voice":
        dr.ellipse(box(-4, -9, 4, -1), fill=primary)
        dr.arc(box(-8, 1, 8, 16), 180, 360, fill=primary, width=lw)
    elif name == "speed":
        dr.arc(box(-9, -7, 9, 11), 180, 360, fill=primary, width=lw)
        dr.line([P(0, 2), P(6, -5)], fill=accent, width=lw)
    elif name == "theme":
        dr.ellipse(box(-9, -9, 9, 9), outline=primary, width=lw)
        dr.pieslice(box(-9, -9, 9, 9), -90, 90, fill=primary)
        if mode != "auto":
            dr.ellipse(box(5, -11, 10, -6), fill=accent)
    elif name == "opacity":
        dr.rectangle(box(-8, -8, 8, 8), outline=primary, width=lw)
        fh = 16.0 * fill
        if fh > 0.5:
            dr.rectangle(box(-8, 8 - fh, 8, 8), fill=accent)
    elif name == "orient":
        for dy in (-4, 4):
            dr.line([P(-7, dy), P(7, dy)], fill=primary, width=lw)
            dr.polygon([P(7, dy), P(4, dy - 2.6), P(4, dy + 2.6)], fill=primary)
            dr.polygon([P(-7, dy), P(-4, dy - 2.6), P(-4, dy + 2.6)],
                       fill=primary)
    elif name == "grip":
        for dx in (-3, 3):
            for dy in (-7, 0, 7):
                dr.ellipse(box(dx - 1.4, dy - 1.4, dx + 1.4, dy + 1.4),
                           fill=primary)
    elif name == "close":
        dr.line([P(-6, -6), P(6, 6)], fill=primary, width=lw)
        dr.line([P(-6, 6), P(6, -6)], fill=primary, width=lw)

    return img.resize((px, px), Image.LANCZOS)


class Tip:
    """Jednoduchý tooltip."""
    def __init__(self, root):
        self.root = root
        self.win = None
        self.after = None

    def show(self, x, y, text, colors, font):
        self.hide()
        self.win = w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        tk.Label(w, text=text, bg=colors["elevate"], fg=colors["fg"],
                 font=font, padx=7, pady=3, bd=0).pack()
        w.update_idletasks()
        w.geometry("+%d+%d" % (x, y))

    def hide(self):
        if self.win is not None:
            self.win.destroy()
            self.win = None


class Panel:
    def __init__(self, root):
        self.root = root
        self.catalog = voice_catalog()
        self.label_by_full = {full: lbl for lbl, full, _ in self.catalog}
        self.meta_by_label = {lbl: (full, g) for lbl, full, g in self.catalog}
        self.borderless = sys.platform != "darwin"
        self.hover = None
        self.st = {}
        self._drag = None
        self._tip_after = None
        self._icon_cache = {}

        fam = {"darwin": "Helvetica Neue", "win32": "Segoe UI"}.get(
            sys.platform, "DejaVu Sans")
        self.font_tip = (fam, 9)
        self.font_badge = (fam, 7, "bold")

        root.title("voice")
        root.attributes("-topmost", True)
        root.resizable(False, False)
        if self.borderless:
            root.overrideredirect(True)
        try:
            root.geometry("+140+140")
        except Exception:
            pass

        s = state.load()
        self.orientation = s.get("panelOrientation") or "h"
        self.theme_mode = s.get("panelTheme") or "auto"
        self.alpha = self._coerce_alpha(s.get("panelAlpha"))
        self.recompute_theme()

        self.cv = tk.Canvas(root, highlightthickness=0, bd=0,
                            bg=self.c["surface"])
        self.cv.pack(fill="both", expand=True)
        self.tip = Tip(root)

        self.cv.bind("<Motion>", self.on_motion)
        self.cv.bind("<Leave>", self.on_leave)
        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_move)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<MouseWheel>", self.on_wheel)
        self.cv.bind("<Button-4>", lambda e: self.on_wheel(e, +1))
        self.cv.bind("<Button-5>", lambda e: self.on_wheel(e, -1))

        self.apply_window()
        self.resize()
        self.sync()

    # ---- helpers -----------------------------------------------------------
    @staticmethod
    def _coerce_alpha(v):
        try:
            a = float(v)
            return a if 0.2 <= a <= 1.0 else 1.0
        except (TypeError, ValueError):
            return 1.0

    def recompute_theme(self):
        dark = detect_dark() if self.theme_mode == "auto" else self.theme_mode == "dark"
        self.c = DARK if dark else LIGHT

    def apply_window(self):
        self.root.configure(bg=self.c["surface"])
        try:
            self.root.attributes("-alpha", self.alpha)
        except Exception:
            pass

    def cell_names(self):
        core = ["power", "mute", "length", "voice", "speed",
                "theme", "opacity", "orient"]
        return (["grip"] + core + ["close"]) if self.borderless else core

    def resize(self):
        n = len(self.cell_names())
        span = MARGIN * 2 + n * CELL + (n - 1) * GAP
        thick = MARGIN * 2 + CELL
        if self.orientation == "v":
            self.cv.config(width=thick, height=span)
        else:
            self.cv.config(width=span, height=thick)

    def cell_rect(self, i):
        if self.orientation == "v":
            x1 = MARGIN
            y1 = MARGIN + i * (CELL + GAP)
        else:
            x1 = MARGIN + i * (CELL + GAP)
            y1 = MARGIN
        return x1, y1, x1 + CELL, y1 + CELL

    def cell_at(self, x, y):
        for i, name in enumerate(self.cell_names()):
            x1, y1, x2, y2 = self.cell_rect(i)
            if x1 <= x <= x2 and y1 <= y <= y2:
                return name
        return None

    # ---- read state for drawing -------------------------------------------
    def rate_value(self):
        try:
            return float(self.st.get("speakingRate") or 1.0)
        except (TypeError, ValueError):
            return 1.0

    # ---- state writes ------------------------------------------------------
    def write(self, **kw):
        s = state.load()
        s.update(kw)
        state.save(s)
        self.sync_now()

    # ---- events ------------------------------------------------------------
    def on_motion(self, e):
        name = self.cell_at(e.x, e.y)
        if name != self.hover:
            self.hover = name
            self.draw()
            self.tip.hide()
            if self._tip_after:
                self.root.after_cancel(self._tip_after)
            if name and name not in ("grip",):
                self._tip_after = self.root.after(
                    450, lambda: self.show_tip(name))

    def on_leave(self, _e):
        self.hover = None
        self.tip.hide()
        self.draw()

    def show_tip(self, name):
        if self.hover != name:
            return
        label, value = self.tip_text(name)
        txt = "%s: %s" % (label, value) if value else label
        self.tip.show(self.root.winfo_pointerx() + 12,
                      self.root.winfo_pointery() + 16,
                      txt, self.c, self.font_tip)

    def on_press(self, e):
        self._press = self.cell_at(e.x, e.y)
        if self._press == "grip":
            self._drag = (e.x_root, e.y_root,
                          self.root.winfo_x(), self.root.winfo_y())

    def on_move(self, e):
        if self._drag:
            ox, oy, wx, wy = self._drag
            self.root.geometry("+%d+%d" % (wx + e.x_root - ox,
                                           wy + e.y_root - oy))

    def on_release(self, e):
        if self._drag:
            self._drag = None
            return
        name = self.cell_at(e.x, e.y)
        if name and name == getattr(self, "_press", None):
            self.dispatch(name, e)
        self._press = None

    def on_wheel(self, e, direction=None):
        if self.cell_at(e.x, e.y) != "speed":
            return
        if direction is None:
            direction = 1 if getattr(e, "delta", 0) > 0 else -1
        cur = self.rate_value()
        new = min(RATE_MAX, max(RATE_MIN, cur + direction * RATE_STEP))
        self.write(speakingRate=round(round(new / RATE_STEP) * RATE_STEP, 2))

    def dispatch(self, name, e):
        if name == "power":
            if self.st.get("enabled"):
                self.write(enabled=False)
            else:
                self.write(enabled=True, muteRemaining=0)
        elif name == "mute":
            self.write(muteRemaining=_next(int(self.st.get("muteRemaining") or 0),
                                           MUTE_CYCLE))
        elif name == "length":
            cur = self.st.get("summaryLength") or "long"
            self.write(summaryLength="short" if cur == "long" else "long")
        elif name == "voice":
            self.voice_menu(e)
        elif name == "speed":
            self.write(speakingRate=round(_next(self.rate_value(), RATE_CYCLE), 2))
        elif name == "theme":
            self.theme_mode = _next(self.theme_mode, THEME_CYCLE)
            self.recompute_theme()
            self.cv.config(bg=self.c["surface"])
            self.write(panelTheme=self.theme_mode)
        elif name == "opacity":
            self.alpha = _next(self.alpha, ALPHA_CYCLE)
            self.apply_window()
            self.write(panelAlpha=self.alpha)
        elif name == "orient":
            self.orientation = "v" if self.orientation == "h" else "h"
            self.resize()
            self.write(panelOrientation=self.orientation)
        elif name == "close":
            self.root.destroy()

    def voice_menu(self, e):
        m = tk.Menu(self.root, tearoff=0, bg=self.c["menu_bg"],
                    fg=self.c["menu_fg"], activebackground=self.c["menu_act"],
                    activeforeground=self.c["menu_fg"], bd=0)
        cur = self.st.get("voiceName") or voices.voice_for_gender(
            self.st.get("gender") or "")
        for lbl, full, g in self.catalog:
            mark = "● " if full == cur else "   "
            m.add_command(label=mark + lbl,
                          command=lambda f=full, gg=g: self.write(
                              voiceName=f, gender=gg))
        m.tk_popup(e.x_root, e.y_root)

    # ---- tooltip text ------------------------------------------------------
    def tip_text(self, name):
        s = self.st
        if name == "power":
            return "Zvuk", "zapnuto" if s.get("enabled") else "vypnuto"
        if name == "mute":
            m = int(s.get("muteRemaining") or 0)
            v = "vypnuto" if m <= 0 else ("do odvolání" if m >= 100000
                                          else "%d tahů" % m)
            return "Ztlumit", v
        if name == "length":
            short = (s.get("summaryLength") or "long") == "short"
            return "Délka", "krátké" if short else "dlouhé"
        if name == "voice":
            full = s.get("voiceName") or voices.voice_for_gender(s.get("gender") or "")
            return "Hlas", self.label_by_full.get(full, "—")
        if name == "speed":
            return "Tempo", "%g×" % round(self.rate_value(), 2)
        if name == "theme":
            return "Téma", {"auto": "auto", "dark": "tmavé",
                            "light": "světlé"}[self.theme_mode]
        if name == "opacity":
            return "Průhlednost", "%d %%" % int(round(self.alpha * 100))
        if name == "orient":
            return "Orientace", "svisle" if self.orientation == "v" else "vodorovně"
        if name == "close":
            return "Zavřít", ""
        return name, ""

    # ---- kreslení ----------------------------------------------------------
    def _round(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.cv.create_polygon(pts, smooth=True, **kw)

    def draw(self):
        c = self.cv
        c.delete("all")
        for i, name in enumerate(self.cell_names()):
            x1, y1, x2, y2 = self.cell_rect(i)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            if name == self.hover and name != "grip":
                self._round(x1 + 1, y1 + 1, x2 - 1, y2 - 1, RAD,
                            fill=self.c["elevate"], outline="")
            self.draw_icon(name, cx, cy, x2, y2)

    def _icon_photo(self, name, primary, accent, mode, fill):
        key = (name, primary, accent, mode, round(fill, 3))
        ph = self._icon_cache.get(key)
        if ph is None:
            img = render_icon(name, CELL, primary, accent, mode, fill)
            buf = io.BytesIO()
            img.save(buf, "PNG")
            ph = tk.PhotoImage(data=base64.b64encode(buf.getvalue()).decode())
            self._icon_cache[key] = ph
        return ph

    def draw_icon(self, name, cx, cy, x2, y2):
        col = self.c
        s = self.st
        if not HAS_PIL:
            return self.draw_icon_vec(name, cx, cy, x2, y2)

        fg, accent = col["fg"], col["accent"]
        primary, mode, fill = fg, "auto", 1.0
        if name == "power":
            primary = col["on"] if s.get("enabled") else col["off"]
        elif name == "mute":
            mode = "active" if int(s.get("muteRemaining") or 0) > 0 else "idle"
            primary = col["amber"] if mode == "active" else fg
        elif name == "length":
            mode = "short" if (s.get("summaryLength") or "long") == "short" \
                else "long"
        elif name == "theme":
            mode = self.theme_mode
        elif name == "opacity":
            fill = self.alpha
        elif name in ("grip", "close"):
            primary = col["dim"]
        self.cv.create_image(cx, cy,
                             image=self._icon_photo(name, primary, accent,
                                                    mode, fill))
        # dynamické popisky (text je AA přes OS)
        if name == "mute":
            m = int(s.get("muteRemaining") or 0)
            if m > 0:
                badge = "∞" if m >= 100000 else str(m)
                self.cv.create_text(x2 - 6, y2 - 7, text=badge,
                                    fill=col["amber"], font=self.font_badge)
        elif name == "speed":
            self.cv.create_text(cx, cy + 9, text="%g×" % round(self.rate_value(),
                                                               2),
                                fill=col["dim"], font=self.font_badge)
        elif name == "opacity" and self.alpha < 0.999:
            self.cv.create_text(cx, cy + 13, text="%d%%" % int(self.alpha * 100),
                                fill=col["dim"], font=self.font_badge)

    def draw_icon_vec(self, name, cx, cy, x2, y2):
        c = self.cv
        col = self.c
        fg, accent = col["fg"], col["accent"]
        s = self.st

        if name == "grip":
            for dx in (-3, 3):
                for dy in (-7, 0, 7):
                    c.create_oval(cx + dx - 1, cy + dy - 1, cx + dx + 1,
                                  cy + dy + 1, fill=col["dim"], outline="")
        elif name == "power":
            on = bool(s.get("enabled"))
            cc = col["on"] if on else col["off"]
            c.create_arc(cx - 9, cy - 9, cx + 9, cy + 9, start=112, extent=316,
                         style="arc", outline=cc, width=2)
            c.create_line(cx, cy - 11, cx, cy - 1, fill=cc, width=2,
                          capstyle="round")
        elif name == "mute":
            m = int(s.get("muteRemaining") or 0)
            active = m > 0
            cc = col["amber"] if active else fg
            c.create_polygon(cx - 8, cy - 3, cx - 3, cy - 3, cx + 1, cy - 8,
                             cx + 1, cy + 8, cx - 3, cy + 3, cx - 8, cy + 3,
                             fill=cc, outline=cc)
            if active:
                c.create_line(cx - 9, cy + 9, cx + 9, cy - 9, fill=cc, width=2,
                              capstyle="round")
                badge = "∞" if m >= 100000 else str(m)
                c.create_text(x2 - 6, y2 - 7, text=badge, fill=col["amber"],
                              font=self.font_badge)
            else:
                for k, rr in ((1, 4), (2, 8)):
                    c.create_arc(cx + 2 - rr, cy - rr, cx + 2 + rr, cy + rr,
                                 start=-55, extent=110, style="arc",
                                 outline=cc, width=1)
        elif name == "length":
            short = (s.get("summaryLength") or "long") == "short"
            rows = [(-3, 8), (3, 4)] if short else [(-8, 9), (-3, 9), (2, 7),
                                                    (7, 5)]
            for dy, w in rows:
                c.create_line(cx - 8, cy + dy, cx - 8 + w + 6, cy + dy,
                              fill=fg, width=2, capstyle="round")
        elif name == "voice":
            c.create_oval(cx - 4, cy - 9, cx + 4, cy - 1, fill=fg, outline=fg)
            c.create_arc(cx - 8, cy + 1, cx + 8, cy + 16, start=0, extent=180,
                         style="arc", outline=fg, width=2)
        elif name == "speed":
            c.create_arc(cx - 9, cy - 7, cx + 9, cy + 11, start=20, extent=140,
                         style="arc", outline=fg, width=2)
            c.create_line(cx, cy + 2, cx + 6, cy - 5, fill=accent, width=2,
                          capstyle="round")
            c.create_text(cx, cy + 9, text="%g×" % round(self.rate_value(), 2),
                          fill=col["dim"], font=self.font_badge)
        elif name == "theme":
            c.create_oval(cx - 9, cy - 9, cx + 9, cy + 9, outline=fg, width=2)
            c.create_arc(cx - 9, cy - 9, cx + 9, cy + 9, start=-90, extent=180,
                         fill=fg, outline=fg)
            if self.theme_mode != "auto":
                c.create_oval(cx + 5, cy - 11, cx + 10, cy - 6,
                              fill=accent, outline="")
        elif name == "opacity":
            c.create_rectangle(cx - 8, cy - 8, cx + 8, cy + 8, outline=fg,
                               width=2)
            fillh = int(16 * self.alpha)
            if fillh > 0:
                c.create_rectangle(cx - 8, cy + 8 - fillh, cx + 8, cy + 8,
                                   fill=accent, outline="")
            if self.alpha < 0.999:
                c.create_text(cx, cy + 13, text="%d%%" % int(self.alpha * 100),
                              fill=col["dim"], font=self.font_badge)
        elif name == "orient":
            c.create_line(cx - 7, cy - 4, cx + 7, cy - 4, fill=fg, width=2,
                          arrow="both", capstyle="round")
            c.create_line(cx - 7, cy + 4, cx + 7, cy + 4, fill=fg, width=2,
                          arrow="both", capstyle="round")
        elif name == "close":
            for a, b in (((-6, -6), (6, 6)), ((-6, 6), (6, -6))):
                c.create_line(cx + a[0], cy + a[1], cx + b[0], cy + b[1],
                              fill=col["dim"], width=2, capstyle="round")

    # ---- sync --------------------------------------------------------------
    def sync_now(self):
        self.st = state.load()
        self.draw()

    def sync(self):
        self.sync_now()
        self.root.after(POLL_MS, self.sync)


def main():
    try:
        root = tk.Tk()
    except tk.TclError as e:
        sys.stderr.write(
            "Nepodařilo se otevřít okno (%s).\n"
            "Na WSL potřebuješ Windows 11 s WSLg.\n" % e)
        sys.exit(1)
    Panel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
