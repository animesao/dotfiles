#!/usr/bin/env python3
"""
cliphist — clipboard history for Wayland
Designed as a noctalia-shell panel
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QSize
from PyQt6.QtGui import (
    QColor, QKeySequence, QPainter, QShortcut,
    QPalette, QPixmap, QIcon, QFont, QFontMetrics
)

DATA_DIR = Path.home() / ".local" / "share" / "cliphist"
HISTORY_FILE = DATA_DIR / "history.json"

# ─── Gruvbox ───
BG       = "#1d2021"
SURFACE  = "#282828"
SURF_HI  = "#3c3836"
HOVER    = "#504945"
BORDER   = "#57514e"
FG       = "#ebdbb2"
FG_DIM   = "#a89984"
FG_FAINT = "#7c6f64"
GREEN    = "#b8bb26"
YELLOW   = "#fabd2f"
RED      = "#fb4934"
AQUA     = "#8ec07c"

R = 12
R_SM = 8


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_history() -> list:
    if HISTORY_FILE.exists():
        try: return json.loads(HISTORY_FILE.read_text())
        except: pass
    return []


def save_history(h):
    HISTORY_FILE.write_text(json.dumps(h, ensure_ascii=False, indent=2))


def get_clip() -> str:
    try:
        r = subprocess.run(["wl-paste", "-t", "text/plain"], capture_output=True, text=True, timeout=2)
        return r.stdout if r.returncode == 0 else ""
    except: return ""


def set_clip(t):
    try: subprocess.run(["wl-copy"], input=t.encode(), check=True, timeout=2)
    except: pass


def mk_icon(svg, color, size=16):
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{svg}</svg>'
    px = QPixmap(size, size); px.fill(Qt.GlobalColor.transparent); px.loadFromData(s.encode())
    return QIcon(px)


class I:
    @staticmethod
    def search(c=FG_DIM): return mk_icon('<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/>', c)
    @staticmethod
    def copy(c=FG_DIM): return mk_icon('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 012-2h10"/>', c)
    @staticmethod
    def pin(c=FG_DIM): return mk_icon('<path d="M12 17v5M9 11l3-7 3 7"/><circle cx="12" cy="9" r="3"/><path d="M5 21h14"/>', c)
    @staticmethod
    def trash(c=FG_DIM): return mk_icon('<path d="M4 7h16M10 11v6M14 11v6"/><path d="M5 7l1 12a2 2 0 002 2h8a2 2 0 002-2l1-12"/><path d="M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3"/>', c)
    @staticmethod
    def close(c=FG_DIM): return mk_icon('<path d="M6 6l12 12M18 6L6 18"/>', c)
    @staticmethod
    def eraser(c=FG_DIM): return mk_icon('<path d="M20 20H9L3 14a1 1 0 010-1.4l8.6-8.6a2 2 0 012.8 0l5.6 5.6a2 2 0 010 2.8L15 20"/><path d="M6 12l8 8"/>', c)


# ─── Item ───
class Item(QWidget):
    def __init__(self, content, ts, pinned, idx):
        super().__init__()
        self.content = content
        self.pinned = pinned
        self._sel = False
        self._hov = False
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(8)

        self.badge = QLabel(str(idx + 1))
        self.badge.setFixedSize(18, 18)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setFont(QFont("Adwaita Sans", 9, QFont.Weight.Bold))
        self._badge()

        is_img = content.startswith("[image:")
        text = "Image" if is_img else content.replace("\n", " ").replace("\r", "")
        text = text[:46] + "…" if len(text) > 46 else text

        self.label = QLabel(text)
        self.label.setFont(QFont("Adwaita Sans", 11))
        self.label.setStyleSheet(f"color: {AQUA if is_img else FG}; background: transparent;")
        self.label.setMaximumWidth(220)

        ts_str = ""
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                now = datetime.now()
                ts_str = dt.strftime("%H:%M") if dt.date() == now.date() else dt.strftime("%d %b")
            except: pass

        self.time = QLabel(ts_str)
        self.time.setFont(QFont("Adwaita Sans", 9))
        self.time.setStyleSheet(f"color: {FG_FAINT}; background: transparent;")

        self.dot = QLabel()
        self.dot.setFixedSize(4, 4)
        self.dot.setStyleSheet(f"background: {YELLOW if pinned else 'transparent'}; border-radius: 2px;")

        lay.addWidget(self.badge)
        lay.addWidget(self.label, 1)
        lay.addWidget(self.time)
        lay.addWidget(self.dot)

    def _badge(self):
        if self._sel:
            self.badge.setStyleSheet(f"background: {GREEN}; color: {BG}; border-radius: 9px;")
        else:
            self.badge.setStyleSheet(f"background: {SURF_HI}; color: {FG_DIM}; border-radius: 9px;")

    def set_selected(self, s):
        self._sel = s; self._badge(); self.update()

    def paintEvent(self, e):
        if self._sel or self._hov:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor(SURF_HI if self._sel else HOVER))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(self.rect()), R_SM, R_SM)
            p.end()

    def enterEvent(self, e): self._hov = True; self.update()
    def leaveEvent(self, e): self._hov = False; self.update()


# ─── Preview ───
class Preview(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(155)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        t = QLabel("PREVIEW")
        t.setFont(QFont("Adwaita Sans", 9, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {FG_FAINT}; letter-spacing: 1px; background: transparent;")
        lay.addWidget(t)

        self.body = QLabel("Select item")
        self.body.setWordWrap(True)
        self.body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.body.setFont(QFont("monospace", 11))
        self.body.setStyleSheet(f"color: {FG_DIM}; background: {BG}; border-radius: {R_SM}px; padding: 8px;")
        lay.addWidget(self.body, 1)

        self.meta = QLabel("")
        self.meta.setFont(QFont("Adwaita Sans", 9))
        self.meta.setStyleSheet(f"color: {FG_FAINT}; background: transparent;")
        lay.addWidget(self.meta)

    def show(self, c):
        if c.startswith("[image:"):
            self.body.setText("Image")
            self.body.setStyleSheet(f"color: {AQUA}; background: {BG}; border-radius: {R_SM}px; padding: 8px;")
            self.meta.setText("image/png")
        else:
            self.body.setText(c[:400])
            self.body.setStyleSheet(f"color: {FG_DIM}; background: {BG}; border-radius: {R_SM}px; padding: 8px;")
            self.meta.setText(f"{len(c)} chars · {c.count(chr(10))+1} lines")

    def empty(self):
        self.body.setText("Select item")
        self.body.setStyleSheet(f"color: {FG_FAINT}; background: {BG}; border-radius: {R_SM}px; padding: 8px;")
        self.meta.setText("")


# ─── Pill ───
class Pill(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Adwaita Sans", 10, QFont.Weight.Bold))
        self.setFixedHeight(22)
        self._s(False)

    def _s(self, ch):
        self.setStyleSheet(f"""
            QPushButton {{ background: {"transparent" if not ch else GREEN}; color: {"FG_FAINT" if not ch else BG}; border: none; border-radius: 11px; padding: 0 12px; }}
            QPushButton:hover {{ background: {"HOVER" if not ch else GREEN}; color: {FG}; }}
        """)

    def nextCheckState(self): super().nextCheckState(); self._s(self.isChecked())


# ─── Window ───
class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.history = []
        self.filtered = []
        self.sel = 0
        self.tab = "all"
        self.items = []
        self._build()
        self._load()
        self._monitor()

    def _build(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(540, 420)

        sf = QFrame(self); sf.setGeometry(4, 4, 532, 412)
        e = QGraphicsDropShadowEffect(); e.setBlurRadius(40); e.setOffset(0, 8)
        c = QColor(BG); c.setAlpha(200); e.setColor(c); sf.setGraphicsEffect(e)

        self.surf = QFrame(self)
        self.surf.setStyleSheet(f"QFrame {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: {R}px; }}")

        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.addWidget(self.surf)
        col = QVBoxLayout(self.surf); col.setContentsMargins(12, 10, 12, 10); col.setSpacing(8)

        # Header
        hdr = QHBoxLayout(); hdr.setSpacing(8)
        dot = QLabel(); dot.setFixedSize(8, 8); dot.setStyleSheet(f"background: {GREEN}; border-radius: 4px;"); hdr.addWidget(dot)
        title = QLabel("Clipboard"); title.setFont(QFont("Adwaita Sans", 13, QFont.Weight.Bold)); title.setStyleSheet(f"color: {FG}; background: transparent;"); hdr.addWidget(title)
        hdr.addStretch()
        self.count = QLabel("0"); self.count.setFont(QFont("Adwaita Sans", 11)); self.count.setStyleSheet(f"color: {FG_FAINT}; background: transparent;"); hdr.addWidget(self.count)
        xb = QPushButton(); xb.setIcon(I.close(FG_FAINT)); xb.setIconSize(QSize(14, 14)); xb.setFixedSize(22, 22); xb.setCursor(Qt.CursorShape.PointingHandCursor)
        xb.setStyleSheet(f"QPushButton {{ background: transparent; border: none; border-radius: 11px; }} QPushButton:hover {{ background: {RED}; }}")
        xb.clicked.connect(self.hide); hdr.addWidget(xb)
        col.addLayout(hdr)

        # Search
        sb = QFrame(); sb.setStyleSheet(f"QFrame {{ background: {BG}; border: 1px solid {BORDER}; border-radius: {R_SM}px; }}")
        sl = QHBoxLayout(sb); sl.setContentsMargins(10, 0, 10, 0); sl.setSpacing(6)
        si = QLabel(); si.setPixmap(I.search(FG_FAINT).pixmap(14, 14)); sl.addWidget(si)
        self.search = QLineEdit(); self.search.setPlaceholderText("search..."); self.search.setFont(QFont("Adwaita Sans", 11))
        self.search.setStyleSheet(f"QLineEdit {{ background: transparent; color: {FG}; border: none; padding: 4px 0; }} QLineEdit::placeholder {{ color: {FG_FAINT}; }}")
        self.search.textChanged.connect(self._refresh); sl.addWidget(self.search, 1)
        col.addWidget(sb)

        # Tabs
        tabs = QHBoxLayout(); tabs.setSpacing(4)
        self.t_all = Pill("All"); self.t_pin = Pill("Pinned"); self.t_txt = Pill("Text")
        self.t_all.setChecked(True)
        self.t_all.clicked.connect(lambda: self._tab("all")); self.t_pin.clicked.connect(lambda: self._tab("pinned")); self.t_txt.clicked.connect(lambda: self._tab("text"))
        tabs.addWidget(self.t_all); tabs.addWidget(self.t_pin); tabs.addWidget(self.t_txt); tabs.addStretch()
        col.addLayout(tabs)

        # Body
        body = QHBoxLayout(); body.setSpacing(8)

        lf = QFrame(); lf.setStyleSheet(f"QFrame {{ background: {BG}; border: 1px solid {BORDER}; border-radius: {R_SM}px; }}")
        ll = QVBoxLayout(lf); ll.setContentsMargins(4, 4, 4, 4); ll.setSpacing(1)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} QScrollBar:vertical {{ background: transparent; width: 4px; }} QScrollBar::handle:vertical {{ background: {HOVER}; border-radius: 2px; min-height: 30px; }} QScrollBar::handle:vertical:hover {{ background: {FG_FAINT}; }} QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}")
        self.list_w = QWidget(); self.list_w.setStyleSheet("background: transparent;")
        self.list_lay = QVBoxLayout(self.list_w); self.list_lay.setContentsMargins(0, 0, 0, 0); self.list_lay.setSpacing(1); self.list_lay.addStretch()
        self.scroll.setWidget(self.list_w); ll.addWidget(self.scroll)
        body.addWidget(lf, 2)

        pf = QFrame(); pf.setStyleSheet(f"QFrame {{ background: {BG}; border: 1px solid {BORDER}; border-radius: {R_SM}px; }}")
        pll = QVBoxLayout(pf); pll.setContentsMargins(0, 0, 0, 0); self.preview = Preview(); pll.addWidget(self.preview)
        body.addWidget(pf, 1)
        col.addLayout(body, 1)

        # Actions
        acts = QHBoxLayout(); acts.setSpacing(6)
        def actbtn(text, color, icon):
            b = QPushButton(); b.setIcon(icon); b.setIconSize(QSize(13, 13)); b.setText(f" {text}")
            b.setFont(QFont("Adwaita Sans", 10, QFont.Weight.Bold)); b.setCursor(Qt.CursorShape.PointingHandCursor); b.setFixedHeight(26)
            b.setStyleSheet(f"QPushButton {{ background: transparent; color: {color}; border: 1px solid {color}30; border-radius: 13px; padding: 0 12px; }} QPushButton:hover {{ background: {color}12; border: 1px solid {color}50; }} QPushButton:pressed {{ background: {color}20; }}")
            return b

        acts.addWidget(actbtn("Copy", GREEN, I.copy(GREEN)))
        acts.addWidget(actbtn("Pin", YELLOW, I.pin(YELLOW)))
        acts.addWidget(actbtn("Delete", RED, I.trash(RED)))
        acts.addStretch()
        acts.addWidget(actbtn("Clear", FG_FAINT, I.eraser(FG_FAINT)))
        col.addLayout(acts)

        QShortcut(QKeySequence("Return"), self, self._copy)
        QShortcut(QKeySequence("Ctrl+P"), self, self._pin)
        QShortcut(QKeySequence("Delete"), self, self._del)
        QShortcut(QKeySequence("Escape"), self, self.hide)
        QShortcut(QKeySequence("Ctrl+F"), self, lambda: self.search.setFocus())
        QShortcut(QKeySequence("1"), self, lambda: self._tab("all"))
        QShortcut(QKeySequence("2"), self, lambda: self._tab("pinned"))
        QShortcut(QKeySequence("3"), self, lambda: self._tab("text"))

    def _tab(self, t):
        self.tab = t
        self.t_all.setChecked(t == "all"); self.t_pin.setChecked(t == "pinned"); self.t_txt.setChecked(t == "text")
        self._refresh()

    def _load(self): self.history = load_history(); self._refresh()

    def _refresh(self):
        for w in self.items: w.setParent(None); w.deleteLater()
        self.items.clear()
        s = sorted(self.history, key=lambda x: (not x.get("pinned", False), x.get("timestamp", "")), reverse=True)
        q = self.search.text().lower()
        self.filtered = []; idx = 0
        for item in s:
            c = item.get("content", ""); p = item.get("pinned", False)
            if q and q not in c.lower(): continue
            if self.tab == "pinned" and not p: continue
            if self.tab == "text" and c.startswith("[image:"): continue
            w = Item(c, item.get("timestamp", ""), p, idx)
            w.mousePressEvent = lambda e, i=idx: self._sel(i)
            w.mouseDoubleClickEvent = lambda e, i=idx: (self._sel(i), self._copy())
            self.list_lay.insertWidget(self.list_lay.count() - 1, w)
            self.items.append(w); self.filtered.append(item); idx += 1
        self.count.setText(str(len(self.items)))
        if self.items: self._sel(0)
        else: self.preview.empty()

    def _sel(self, i):
        self.sel = i
        for j, w in enumerate(self.items): w.set_selected(j == i)
        if i < len(self.filtered): self.preview.show(self.filtered[i].get("content", ""))

    def _copy(self):
        if self.sel >= len(self.filtered): return
        c = self.filtered[self.sel].get("content", "")
        if c.startswith("[image:"):
            p = c.replace("[image:", "").replace("]", "")
            if os.path.exists(p):
                try:
                    d = Path(p).read_bytes()
                    proc = subprocess.Popen(["wl-copy", "-t", "image/png"], stdin=subprocess.PIPE)
                    proc.communicate(input=d)
                except: pass
        else: set_clip(c)
        self._flash("Copied", GREEN)
        QTimer.singleShot(200, self.hide)

    def _pin(self):
        if self.sel >= len(self.filtered): return
        item = self.filtered[self.sel]; item["pinned"] = not item.get("pinned", False)
        for h in self.history:
            if h.get("content") == item.get("content"): h["pinned"] = item["pinned"]; break
        save_history(self.history); self._refresh()
        self._flash("Pinned" if item["pinned"] else "Unpinned", YELLOW)

    def _del(self):
        if self.sel >= len(self.filtered): return
        item = self.filtered[self.sel]
        self.history = [h for h in self.history if h.get("content") != item.get("content")]
        save_history(self.history); self._refresh(); self._flash("Deleted", RED)

    def _clear(self):
        self.history = []; save_history(self.history); self._refresh(); self._flash("Cleared", FG_FAINT)

    def _flash(self, msg, color):
        self.count.setText(msg); self.count.setStyleSheet(f"color: {color}; font-weight: bold; background: transparent;")
        QTimer.singleShot(1500, lambda: self.count.setStyleSheet(f"color: {FG_FAINT}; background: transparent;"))

    def show_window(self):
        self._load(); self.search.clear(); self.search.setFocus(); self._tab("all")
        s = QApplication.primaryScreen().geometry()
        self.move((s.width()-self.width())//2, (s.height()-self.height())//2)
        self.show(); self.raise_(); self.activateWindow()

    def _monitor(self):
        self.timer = QTimer(); self.timer.timeout.connect(self._check); self.timer.start(1000); self._last = get_clip()

    def _check(self):
        c = get_clip()
        if c and c != self._last:
            if not any(h.get("content") == c for h in self.history):
                self.history.insert(0, {"content": c, "timestamp": datetime.now().isoformat(), "pinned": False})
                if len(self.history) > 500: self.history = self.history[:500]
                save_history(self.history)
                if self.isVisible(): self._refresh()
            self._last = c

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Escape: self.hide()
        elif k == Qt.Key.Key_Down:
            if self.sel < len(self.filtered)-1: self._sel(self.sel+1); self.scroll.ensureWidgetVisible(self.items[self.sel])
        elif k == Qt.Key.Key_Up:
            if self.sel > 0: self._sel(self.sel-1); self.scroll.ensureWidgetVisible(self.items[self.sel])
        elif k == Qt.Key.Key_PageDown: self._sel(min(self.sel+10, len(self.filtered)-1))
        elif k == Qt.Key.Key_PageUp: self._sel(max(self.sel-10, 0))
        elif k == Qt.Key.Key_Home: self._sel(0)
        elif k == Qt.Key.Key_End: self._sel(max(0, len(self.filtered)-1))
        else: super().keyPressEvent(e)


def main():
    ensure_dirs()
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list":
            for i, item in enumerate(load_history()[:20]):
                print(f"{i+1:3d}. {item.get('content', '')[:60].replace(chr(10), ' ')}")
        elif cmd == "count": print(f"{len(load_history())} items")
        elif cmd == "clear": save_history([]); print("Cleared")
        return

    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False)
    p = QPalette(); p.setColor(QPalette.ColorRole.Window, QColor(SURFACE)); p.setColor(QPalette.ColorRole.WindowText, QColor(FG)); p.setColor(QPalette.ColorRole.Base, QColor(BG)); p.setColor(QPalette.ColorRole.Text, QColor(FG)); app.setPalette(p)
    w = Window(); w.show_window(); sys.exit(app.exec())


if __name__ == "__main__":
    main()
