#!/usr/bin/env python3
"""
cliphist — clipboard history for Wayland
Gruvbox theme, FontAwesome icons
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
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QKeySequence, QPainter, QPainterPath, QShortcut, QPalette, QFont, QPen, QBrush

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
BLUE     = "#83a598"
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


# ─── SVG Icons ───
class Icon:
    @staticmethod
    def copy(color=FG_DIM, size=16):
        return Icon._svg(f'''
            <path d="M8 1H4a1 1 0 00-1 1v4" stroke="{color}" fill="none" stroke-width="1.5" stroke-linecap="round"/>
            <rect x="5" y="3" width="8" height="10" rx="1.5" stroke="{color}" fill="none" stroke-width="1.5"/>
        ''', color, size)

    @staticmethod
    def pin(color=FG_DIM, size=16):
        return Icon._svg(f'''
            <circle cx="8" cy="4" r="2" stroke="{color}" fill="none" stroke-width="1.5"/>
            <path d="M8 6v6M6 10h4" stroke="{color}" fill="none" stroke-width="1.5" stroke-linecap="round"/>
        ''', color, size)

    @staticmethod
    def trash(color=FG_DIM, size=16):
        return Icon._svg(f'''
            <path d="M3 4h10M5 4V3a1 1 0 011-1h4a1 1 0 011 1v1" stroke="{color}" fill="none" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M4 4l.7 9.1a1 1 0 001 .9h4.6a1 1 0 001-.9L12 4" stroke="{color}" fill="none" stroke-width="1.5"/>
        ''', color, size)

    @staticmethod
    def search(color=FG_DIM, size=16):
        return Icon._svg(f'''
            <circle cx="7" cy="7" r="4" stroke="{color}" fill="none" stroke-width="1.5"/>
            <path d="M10 10l3 3" stroke="{color}" fill="none" stroke-width="1.5" stroke-linecap="round"/>
        ''', color, size)

    @staticmethod
    def close(color=FG_DIM, size=16):
        return Icon._svg(f'''
            <path d="M4 4l8 8M12 4l-8 8" stroke="{color}" fill="none" stroke-width="1.5" stroke-linecap="round"/>
        ''', color, size)

    @staticmethod
    def eraser(color=FG_DIM, size=16):
        return Icon._svg(f'''
            <path d="M5 13h6M3 9l4-7h2l4 7-5 5H4a1 1 0 01-1-1V10a1 1 0 011-1z" stroke="{color}" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        ''', color, size)

    @staticmethod
    def clipboard(color=FG, size=18):
        return Icon._svg(f'''
            <rect x="3" y="2" width="10" height="12" rx="1.5" stroke="{color}" fill="none" stroke-width="1.5"/>
            <path d="M6 2V1.5A.5.5 0 016.5 1h3a.5.5 0 01.5.5V2" stroke="{color}" fill="none" stroke-width="1.5"/>
        ''', color, size)

    @staticmethod
    def _svg(path, color, size):
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 16 16">{path}</svg>'''
        pixmap = QPixmap()
        pixmap.loadFromData(svg.encode())
        return QIcon(pixmap)


from PyQt6.QtGui import QPixmap, QIcon


# ─── Icon Button ───
class IconButton(QPushButton):
    def __init__(self, icon_fn, tooltip="", color=FG_DIM, bg_color=None, size=32):
        super().__init__()
        self.icon_fn = icon_fn
        self.tooltip_text = tooltip
        self.color = color
        self.bg_color = bg_color
        self._hover = False
        self._pressed = False

        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setIcon(icon_fn(color, 16))
        self.setIconSize(QPixmap(16, 16).size())

        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: {size // 2}px;
            }}
            QPushButton:hover {{
                background: {HOVER};
            }}
            QPushButton:pressed {{
                background: {SURF_HI};
            }}
        """)

    def set_color(self, color):
        self.color = color
        self.setIcon(self.icon_fn(color, 16))


# ─── Action Button ───
class ActionButton(QPushButton):
    def __init__(self, text, color=FG_DIM, icon_fn=None):
        super().__init__()
        self.color = color

        if icon_fn:
            self.setIcon(icon_fn(color, 14))
            self.setIconSize(QPixmap(14, 14).size())
            self.setText(f"  {text}")
        else:
            self.setText(text)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(28)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: 1px solid {color}30;
                border-radius: 14px;
                padding: 0 14px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {color}15;
                border: 1px solid {color}50;
            }}
            QPushButton:pressed {{
                background: {color}22;
            }}
        """)


# ─── Item Widget ───
class ItemWidget(QWidget):
    def __init__(self, content, ts, pinned, idx):
        super().__init__()
        self.content = content
        self.pinned = pinned
        self._sel = False
        self._hov = False

        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(8)

        # Badge
        self.badge = QLabel(str(idx + 1))
        self.badge.setFixedSize(20, 20)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._style_badge()

        # Content
        is_img = content.startswith("[image:")
        text = "Image" if is_img else content.replace("\n", " ").replace("\r", "")
        text = text[:52] + "…" if len(text) > 52 else text

        self.label = QLabel(text)
        self.label.setStyleSheet(f"color: {AQUA if is_img else FG}; background: transparent; font-size: 12px;")
        self.label.setMaximumWidth(250)

        # Time
        ts_str = ""
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                now = datetime.now()
                ts_str = dt.strftime("%H:%M") if dt.date() == now.date() else dt.strftime("%d %b")
            except: pass

        self.time = QLabel(ts_str)
        self.time.setStyleSheet(f"color: {FG_FAINT}; background: transparent; font-size: 10px;")

        # Pin dot
        self.dot = QLabel()
        self.dot.setFixedSize(5, 5)
        self.dot.setStyleSheet(f"background: {YELLOW if pinned else 'transparent'}; border-radius: 2px;")

        lay.addWidget(self.badge)
        lay.addWidget(self.label, 1)
        lay.addWidget(self.time)
        lay.addWidget(self.dot)

    def _style_badge(self):
        if self._sel:
            self.badge.setStyleSheet(f"background: {GREEN}; color: {BG}; border-radius: 10px; font-size: 10px; font-weight: bold;")
        else:
            self.badge.setStyleSheet(f"background: {SURF_HI}; color: {FG_DIM}; border-radius: 10px; font-size: 9px;")

    def set_selected(self, s):
        self._sel = s
        self._style_badge()
        self.update()

    def paintEvent(self, e):
        if self._sel or self._hov:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor(SURF_HI if self._sel else HOVER))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(self.rect()), R_SM, R_SM)
            p.end()

    def enterEvent(self, e):
        self._hov = True; self.update()

    def leaveEvent(self, e):
        self._hov = False; self.update()


# ─── Preview ───
class Preview(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(170)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        t = QLabel("PREVIEW")
        t.setStyleSheet(f"color: {FG_FAINT}; font-size: 9px; font-weight: bold; letter-spacing: 1px; background: transparent;")
        lay.addWidget(t)

        self.body = QLabel("Select item")
        self.body.setWordWrap(True)
        self.body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.body.setStyleSheet(f"color: {FG_DIM}; font-size: 11px; background: {BG}; border-radius: {R_SM}px; padding: 10px; font-family: monospace;")
        lay.addWidget(self.body, 1)

        self.meta = QLabel("")
        self.meta.setStyleSheet(f"color: {FG_FAINT}; font-size: 10px; background: transparent;")
        lay.addWidget(self.meta)

    def show_content(self, c):
        if c.startswith("[image:"):
            self.body.setText("Image")
            self.body.setStyleSheet(f"color: {AQUA}; font-size: 11px; background: {BG}; border-radius: {R_SM}px; padding: 10px;")
            self.meta.setText("image/png")
        else:
            self.body.setText(c[:400])
            self.body.setStyleSheet(f"color: {FG_DIM}; font-size: 11px; background: {BG}; border-radius: {R_SM}px; padding: 10px; font-family: monospace;")
            self.meta.setText(f"{len(c)} chars · {c.count(chr(10))+1} lines")

    def clear(self):
        self.body.setText("Select item")
        self.body.setStyleSheet(f"color: {FG_FAINT}; font-size: 11px; background: {BG}; border-radius: {R_SM}px; padding: 10px;")
        self.meta.setText("")


# ─── Pill ───
class Pill(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(24)
        self._style(False)

    def _style(self, ch):
        self.setStyleSheet(f"""
            QPushButton {{
                background: {"transparent" if not ch else GREEN};
                color: {"FG_FAINT" if not ch else BG};
                border: none; border-radius: 12px;
                padding: 0 12px; font-size: 11px; {"font-weight: bold;" if ch else ""}
            }}
            QPushButton:hover {{ background: {"HOVER" if not ch else GREEN}; color: {FG}; }}
        """)

    def nextCheckState(self):
        super().nextCheckState(); self._style(self.isChecked())


# ─── Window ───
class Window(QWidget):
    closed = pyqtSignal()

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
        self.setFixedSize(580, 460)

        # Shadow
        sf = QFrame(self)
        sf.setGeometry(4, 4, 572, 452)
        e = QGraphicsDropShadowEffect()
        e.setBlurRadius(40); e.setOffset(0, 8)
        c = QColor(BG); c.setAlpha(200); e.setColor(c)
        sf.setGraphicsEffect(e)

        # Surface
        self.surf = QFrame(self)
        self.surf.setStyleSheet(f"QFrame {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: {R}px; }}")

        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.addWidget(self.surf)
        col = QVBoxLayout(self.surf); col.setContentsMargins(14, 12, 14, 12); col.setSpacing(8)

        # Header
        hdr = QHBoxLayout(); hdr.setSpacing(8)
        dot = QLabel(); dot.setFixedSize(8, 8); dot.setStyleSheet(f"background: {GREEN}; border-radius: 4px;"); hdr.addWidget(dot)
        title = QLabel("Clipboard"); title.setStyleSheet(f"color: {FG}; font-size: 14px; font-weight: bold; background: transparent;"); hdr.addWidget(title)
        hdr.addStretch()
        self.count = QLabel("0"); self.count.setStyleSheet(f"color: {FG_FAINT}; font-size: 12px; background: transparent;"); hdr.addWidget(self.count)
        x_btn = IconButton(Icon.close, "Close (Esc)", FG_FAINT, size=22)
        x_btn.clicked.connect(self.hide)
        hdr.addWidget(x_btn)
        col.addLayout(hdr)

        # Search
        sb = QFrame(); sb.setStyleSheet(f"QFrame {{ background: {BG}; border: 1px solid {BORDER}; border-radius: {R_SM}px; }}")
        sl = QHBoxLayout(sb); sl.setContentsMargins(10, 0, 10, 0); sl.setSpacing(6)
        si = QLabel(); si.setPixmap(Icon.search(FG_FAINT, 14).pixmap(14, 14)); sl.addWidget(si)
        self.search = QLineEdit(); self.search.setPlaceholderText("search..."); self.search.setStyleSheet(f"QLineEdit {{ background: transparent; color: {FG}; border: none; font-size: 12px; padding: 5px 0; }} QLineEdit::placeholder {{ color: {FG_FAINT}; }}")
        self.search.textChanged.connect(self._refresh)
        sl.addWidget(self.search, 1)
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

        # List
        lf = QFrame(); lf.setStyleSheet(f"QFrame {{ background: {BG}; border: 1px solid {BORDER}; border-radius: {R_SM}px; }}")
        ll = QVBoxLayout(lf); ll.setContentsMargins(4, 4, 4, 4); ll.setSpacing(1)

        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} QScrollBar:vertical {{ background: transparent; width: 4px; }} QScrollBar::handle:vertical {{ background: {HOVER}; border-radius: 2px; min-height: 30px; }} QScrollBar::handle:vertical:hover {{ background: {FG_FAINT}; }} QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}")

        self.list_w = QWidget(); self.list_w.setStyleSheet("background: transparent;")
        self.list_lay = QVBoxLayout(self.list_w); self.list_lay.setContentsMargins(0, 0, 0, 0); self.list_lay.setSpacing(1); self.list_lay.addStretch()
        self.scroll.setWidget(self.list_w); ll.addWidget(self.scroll)
        body.addWidget(lf, 2)

        # Preview
        pf = QFrame(); pf.setStyleSheet(f"QFrame {{ background: {BG}; border: 1px solid {BORDER}; border-radius: {R_SM}px; }}")
        pll = QVBoxLayout(pf); pll.setContentsMargins(0, 0, 0, 0)
        self.preview = Preview(); pll.addWidget(self.preview)
        body.addWidget(pf, 1)
        col.addLayout(body, 1)

        # Actions
        acts = QHBoxLayout(); acts.setSpacing(6)
        self.btn_c = ActionButton("Copy", GREEN, Icon.copy)
        self.btn_p = ActionButton("Pin", YELLOW, Icon.pin)
        self.btn_d = ActionButton("Delete", RED, Icon.trash)
        acts.addWidget(self.btn_c); acts.addWidget(self.btn_p); acts.addWidget(self.btn_d); acts.addStretch()
        acts.addWidget(ActionButton("Clear", FG_FAINT, Icon.eraser))
        col.addLayout(acts)

        # Keys
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

    def _load(self):
        self.history = load_history(); self._refresh()

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
            w = ItemWidget(c, item.get("timestamp", ""), p, idx)
            w.mousePressEvent = lambda e, i=idx: self._select(i)
            self.list_lay.insertWidget(self.list_lay.count() - 1, w)
            self.items.append(w); self.filtered.append(item); idx += 1
        self.count.setText(str(len(self.items)))
        if self.items: self._select(0)
        else: self.preview.clear()

    def _select(self, i):
        self.sel = i
        for j, w in enumerate(self.items): w.set_selected(j == i)
        if i < len(self.filtered): self.preview.show_content(self.filtered[i].get("content", ""))

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
        self.count.setText(msg); self.count.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; background: transparent;")
        QTimer.singleShot(1500, lambda: self.count.setStyleSheet(f"color: {FG_FAINT}; font-size: 12px; background: transparent;"))

    def show_window(self):
        self._load(); self.search.clear(); self.search.setFocus(); self._tab("all")
        s = QApplication.primaryScreen().geometry()
        self.move((s.width()-self.width())//2, (s.height()-self.height())//2)
        self.show(); self.raise_(); self.activateWindow()

    def _monitor(self):
        self.timer = QTimer(); self.timer.timeout.connect(self._check); self.timer.start(1000)
        self._last = get_clip()

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
            if self.sel < len(self.filtered)-1: self._select(self.sel+1); self.scroll.ensureWidgetVisible(self.items[self.sel])
        elif k == Qt.Key.Key_Up:
            if self.sel > 0: self._select(self.sel-1); self.scroll.ensureWidgetVisible(self.items[self.sel])
        elif k == Qt.Key.Key_PageDown: self._select(min(self.sel+10, len(self.filtered)-1))
        elif k == Qt.Key.Key_PageUp: self._select(max(self.sel-10, 0))
        elif k == Qt.Key.Key_Home: self._select(0)
        elif k == Qt.Key.Key_End: self._select(max(0, len(self.filtered)-1))
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
