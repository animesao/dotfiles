#!/usr/bin/env python3
"""
cliphist — clipboard history for Wayland
Designed to match noctalia-shell / Gruvbox aesthetic
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
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QKeySequence, QPainter, QShortcut, QPalette

DATA_DIR = Path.home() / ".local" / "share" / "cliphist"
HISTORY_FILE = DATA_DIR / "history.json"
IMAGES_DIR = DATA_DIR / "images"

# ─── Gruvbox palette (from noctalia colors.json) ───
# Surface hierarchy: bg < surface < surfaceVariant
# Accent hierarchy: primary (green), secondary (yellow), tertiary (blue)
# Text hierarchy: onSurface (bright), onSurfaceVariant (dim), outline (faint)

BG           = "#1d2021"   # deepest background
SURFACE      = "#282828"   # main surface
SURFACE_HI   = "#3c3836"   # elevated surface
HOVER        = "#504945"   # hover state
BORDER       = "#57514e"   # borders, dividers

FG           = "#ebdbb2"   # primary text
FG_DIM       = "#a89984"   # secondary text
FG_FAINT     = "#7c6f64"   # tertiary/disabled

GREEN        = "#b8bb26"   # primary accent
YELLOW       = "#fabd2f"   # secondary accent
BLUE         = "#83a598"   # tertiary accent
RED          = "#fb4934"   # error/delete
AQUA         = "#8ec07c"   # special

RADIUS       = 12
RADIUS_SM    = 8


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_history(history: list):
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2))


def get_clipboard_text() -> str:
    try:
        r = subprocess.run(["wl-paste", "-t", "text/plain"],
                           capture_output=True, text=True, timeout=2)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def copy_to_clipboard(text: str):
    try:
        subprocess.run(["wl-copy"], input=text.encode(), check=True, timeout=2)
    except Exception:
        pass


# ─── Item Widget ───
class ItemWidget(QWidget):
    def __init__(self, content: str, timestamp: str, pinned: bool, index: int):
        super().__init__()
        self.content = content
        self.pinned = pinned
        self._selected = False
        self._hover = False

        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(10)

        # Number badge — noctalia capsule style
        self.badge = QLabel(str(index + 1))
        self.badge.setFixedSize(22, 22)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._style_badge()

        # Content
        is_img = content.startswith("[image:")
        text = "Image" if is_img else content.replace("\n", " ").replace("\r", "")
        text = text[:58] + "…" if len(text) > 58 else text

        self.label = QLabel(text)
        self.label.setStyleSheet(f"color: {FG}; font-size: 13px; background: transparent;")
        self.label.setMaximumWidth(280)

        # Timestamp
        ts = ""
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                now = datetime.now()
                ts = dt.strftime("%H:%M") if dt.date() == now.date() else dt.strftime("%d %b")
            except ValueError:
                pass

        self.time = QLabel(ts)
        self.time.setStyleSheet(f"color: {FG_FAINT}; font-size: 11px; background: transparent;")

        # Pin marker
        self.pin = QLabel()
        self.pin.setFixedSize(6, 6)
        self.pin.setStyleSheet(f"background: {YELLOW}; border-radius: 3px;") if pinned else \
            self.pin.setStyleSheet("background: transparent;")

        lay.addWidget(self.badge)
        lay.addWidget(self.label, 1)
        lay.addWidget(self.time)
        lay.addWidget(self.pin)

    def _style_badge(self):
        if self._selected:
            self.badge.setStyleSheet(f"""
                background: {GREEN};
                color: {BG};
                border-radius: 11px;
                font-size: 11px;
                font-weight: bold;
            """)
        else:
            self.badge.setStyleSheet(f"""
                background: {SURFACE_HI};
                color: {FG_DIM};
                border-radius: 11px;
                font-size: 10px;
            """)

    def set_selected(self, s: bool):
        self._selected = s
        self._style_badge()
        self.update()

    def paintEvent(self, event):
        if self._selected or self._hover:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            color = QColor(SURFACE_HI if self._selected else HOVER)
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(self.rect(), RADIUS_SM, RADIUS_SM)
            p.end()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()


# ─── Preview ───
class Preview(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(170)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        title = QLabel("PREVIEW")
        title.setStyleSheet(f"color: {FG_FAINT}; font-size: 10px; font-weight: bold; background: transparent;")
        lay.addWidget(title)

        self.body = QLabel("Select an item")
        self.body.setWordWrap(True)
        self.body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.body.setStyleSheet(f"""
            color: {FG_DIM};
            font-size: 12px;
            background: {BG};
            border-radius: {RADIUS_SM}px;
            padding: 10px;
            font-family: monospace;
        """)
        lay.addWidget(self.body, 1)

        self.meta = QLabel("")
        self.meta.setStyleSheet(f"color: {FG_FAINT}; font-size: 10px; background: transparent;")
        lay.addWidget(self.meta)

    def show_content(self, content: str):
        if content.startswith("[image:"):
            self.body.setText("Image")
            self.body.setStyleSheet(f"""
                color: {AQUA};
                font-size: 12px;
                background: {BG};
                border-radius: {RADIUS_SM}px;
                padding: 10px;
            """)
            self.meta.setText("image/png")
        else:
            self.body.setText(content[:400])
            self.body.setStyleSheet(f"""
                color: {FG_DIM};
                font-size: 12px;
                background: {BG};
                border-radius: {RADIUS_SM}px;
                padding: 10px;
                font-family: monospace;
            """)
            lines = content.count("\n") + 1
            self.meta.setText(f"{len(content)} chars · {lines} lines")

    def clear(self):
        self.body.setText("Select an item")
        self.body.setStyleSheet(f"""
            color: {FG_FAINT};
            font-size: 12px;
            background: {BG};
            border-radius: {RADIUS_SM}px;
            padding: 10px;
        """)
        self.meta.setText("")


# ─── Pill Tab ───
class Pill(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(28)
        self._style(False)

    def _style(self, checked):
        self.setStyleSheet(f"""
            QPushButton {{
                background: {"transparent" if not checked else GREEN};
                color: {"FG_FAINT" if not checked else BG};
                border: none;
                border-radius: {RADIUS_SM}px;
                padding: 4px 14px;
                font-size: 11px;
                {"font-weight: bold;" if checked else ""}
            }}
            QPushButton:hover {{
                background: {"HOVER" if not checked else GREEN};
                color: {FG};
            }}
        """)

    def nextCheckState(self):
        super().nextCheckState()
        self._style(self.isChecked())


# ─── Main Window ───
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
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(620, 500)

        # Shadow layer
        shadow_frame = QFrame(self)
        shadow_frame.setGeometry(4, 4, 612, 492)
        eff = QGraphicsDropShadowEffect()
        eff.setBlurRadius(32)
        eff.setOffset(0, 6)
        c = QColor(BG)
        c.setAlpha(180)
        eff.setColor(c)
        shadow_frame.setGraphicsEffect(eff)

        # Main surface
        self.surface = QFrame(self)
        self.surface.setStyleSheet(f"""
            QFrame {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: {RADIUS}px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.surface)

        col = QVBoxLayout(self.surface)
        col.setContentsMargins(14, 14, 14, 14)
        col.setSpacing(10)

        # ── Header ──
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background: {GREEN}; border-radius: 5px;")
        hdr.addWidget(dot)

        title = QLabel("Clipboard")
        title.setStyleSheet(f"color: {FG}; font-size: 15px; font-weight: bold; background: transparent;")
        hdr.addWidget(title)

        hdr.addStretch()

        self.count = QLabel("0")
        self.count.setStyleSheet(f"color: {FG_FAINT}; font-size: 12px; background: transparent;")
        hdr.addWidget(self.count)

        close = QPushButton("×")
        close.setFixedSize(24, 24)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {FG_FAINT};
                border: none;
                border-radius: 12px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {RED};
                color: {BG};
            }}
        """)
        close.clicked.connect(self.hide)
        hdr.addWidget(close)

        col.addLayout(hdr)

        # ── Search ──
        search_bg = QFrame()
        search_bg.setStyleSheet(f"""
            QFrame {{
                background: {BG};
                border: 1px solid {BORDER};
                border-radius: {RADIUS_SM}px;
            }}
        """)
        sb = QHBoxLayout(search_bg)
        sb.setContentsMargins(10, 0, 10, 0)
        sb.setSpacing(8)

        magnifier = QLabel(">")
        magnifier.setFixedSize(18, 18)
        magnifier.setAlignment(Qt.AlignmentFlag.AlignCenter)
        magnifier.setStyleSheet(f"""
            color: {FG_FAINT};
            font-size: 11px;
            font-family: monospace;
            background: transparent;
        """)
        sb.addWidget(magnifier)

        self.search = QLineEdit()
        self.search.setPlaceholderText("search...")
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {FG};
                border: none;
                font-size: 13px;
                padding: 6px 0;
            }}
            QLineEdit::placeholder {{
                color: {FG_FAINT};
            }}
        """)
        self.search.textChanged.connect(self._refresh)
        sb.addWidget(self.search, 1)

        col.addWidget(search_bg)

        # ── Tabs ──
        tabs = QHBoxLayout()
        tabs.setSpacing(4)
        self.t_all = Pill("All")
        self.t_pin = Pill("Pinned")
        self.t_txt = Pill("Text")
        self.t_all.setChecked(True)
        self.t_all.clicked.connect(lambda: self._tab("all"))
        self.t_pin.clicked.connect(lambda: self._tab("pinned"))
        self.t_txt.clicked.connect(lambda: self._tab("text"))
        tabs.addWidget(self.t_all)
        tabs.addWidget(self.t_pin)
        tabs.addWidget(self.t_txt)
        tabs.addStretch()
        col.addLayout(tabs)

        # ── List + Preview ──
        body = QHBoxLayout()
        body.setSpacing(10)

        # List container
        list_frame = QFrame()
        list_frame.setStyleSheet(f"""
            QFrame {{
                background: {BG};
                border: 1px solid {BORDER};
                border-radius: {RADIUS_SM}px;
            }}
        """)
        lf = QVBoxLayout(list_frame)
        lf.setContentsMargins(4, 4, 4, 4)
        lf.setSpacing(1)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {HOVER};
                border-radius: 2px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {FG_FAINT};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self.list_w = QWidget()
        self.list_w.setStyleSheet("background: transparent;")
        self.list_lay = QVBoxLayout(self.list_w)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(1)
        self.list_lay.addStretch()

        self.scroll.setWidget(self.list_w)
        lf.addWidget(self.scroll)
        body.addWidget(list_frame, 2)

        # Preview
        prev_frame = QFrame()
        prev_frame.setStyleSheet(f"""
            QFrame {{
                background: {BG};
                border: 1px solid {BORDER};
                border-radius: {RADIUS_SM}px;
            }}
        """)
        pf = QVBoxLayout(prev_frame)
        pf.setContentsMargins(0, 0, 0, 0)
        self.preview = Preview()
        pf.addWidget(self.preview)
        body.addWidget(prev_frame, 1)

        col.addLayout(body, 1)

        # ── Actions ──
        acts = QHBoxLayout()
        acts.setSpacing(6)

        self.btn_c = self._act("Copy", GREEN, self._copy)
        self.btn_p = self._act("Pin", YELLOW, self._pin)
        self.btn_d = self._act("Delete", RED, self._del)

        acts.addWidget(self.btn_c)
        acts.addWidget(self.btn_p)
        acts.addWidget(self.btn_d)
        acts.addStretch()
        acts.addWidget(self._act("Clear", FG_FAINT, self._clear))

        col.addLayout(acts)

        # ── Keys ──
        QShortcut(QKeySequence("Return"), self, self._copy)
        QShortcut(QKeySequence("Ctrl+P"), self, self._pin)
        QShortcut(QKeySequence("Delete"), self, self._del)
        QShortcut(QKeySequence("Escape"), self, self.hide)
        QShortcut(QKeySequence("Ctrl+F"), self, lambda: self.search.setFocus())
        QShortcut(QKeySequence("1"), self, lambda: self._tab("all"))
        QShortcut(QKeySequence("2"), self, lambda: self._tab("pinned"))
        QShortcut(QKeySequence("3"), self, lambda: self._tab("text"))

    def _act(self, text, color, cb):
        b = QPushButton(text)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFixedHeight(28)
        b.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: 1px solid {color}44;
                border-radius: {RADIUS_SM}px;
                padding: 4px 14px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {color}22;
                border: 1px solid {color}66;
            }}
            QPushButton:pressed {{
                background: {color}33;
            }}
        """)
        b.clicked.connect(cb)
        return b

    def _tab(self, t):
        self.tab = t
        self.t_all.setChecked(t == "all")
        self.t_pin.setChecked(t == "pinned")
        self.t_txt.setChecked(t == "text")
        self._refresh()

    def _load(self):
        self.history = load_history()
        self._refresh()

    def _refresh(self):
        for w in self.items:
            w.setParent(None)
            w.deleteLater()
        self.items.clear()

        s = sorted(self.history, key=lambda x: (not x.get("pinned", False), x.get("timestamp", "")), reverse=True)
        q = self.search.text().lower()

        self.filtered = []
        idx = 0
        for item in s:
            c = item.get("content", "")
            p = item.get("pinned", False)
            if q and q not in c.lower():
                continue
            if self.tab == "pinned" and not p:
                continue
            if self.tab == "text" and c.startswith("[image:"):
                continue

            w = ItemWidget(c, item.get("timestamp", ""), p, idx)
            w.mousePressEvent = lambda e, i=idx: self._select(i)
            self.list_lay.insertWidget(self.list_lay.count() - 1, w)
            self.items.append(w)
            self.filtered.append(item)
            idx += 1

        self.count.setText(f"{len(self.items)}")

        if self.items:
            self._select(0)
        else:
            self.preview.clear()

    def _select(self, i):
        self.sel = i
        for j, w in enumerate(self.items):
            w.set_selected(j == i)
        if i < len(self.filtered):
            self.preview.show_content(self.filtered[i].get("content", ""))

    def _copy(self):
        if self.sel >= len(self.filtered):
            return
        c = self.filtered[self.sel].get("content", "")
        if c.startswith("[image:"):
            p = c.replace("[image:", "").replace("]", "")
            if os.path.exists(p):
                try:
                    d = Path(p).read_bytes()
                    proc = subprocess.Popen(["wl-copy", "-t", "image/png"], stdin=subprocess.PIPE)
                    proc.communicate(input=d)
                except Exception:
                    pass
        else:
            copy_to_clipboard(c)
        self._flash("Copied", GREEN)

    def _pin(self):
        if self.sel >= len(self.filtered):
            return
        item = self.filtered[self.sel]
        item["pinned"] = not item.get("pinned", False)
        for h in self.history:
            if h.get("content") == item.get("content"):
                h["pinned"] = item["pinned"]
                break
        save_history(self.history)
        self._refresh()
        self._flash("Pinned" if item["pinned"] else "Unpinned", YELLOW)

    def _del(self):
        if self.sel >= len(self.filtered):
            return
        item = self.filtered[self.sel]
        self.history = [h for h in self.history if h.get("content") != item.get("content")]
        save_history(self.history)
        self._refresh()
        self._flash("Deleted", RED)

    def _clear(self):
        self.history = []
        save_history(self.history)
        self._refresh()
        self._flash("Cleared", FG_FAINT)

    def _flash(self, msg, color):
        self.count.setText(msg)
        self.count.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; background: transparent;")
        QTimer.singleShot(1500, lambda: self.count.setStyleSheet(
            f"color: {FG_FAINT}; font-size: 12px; background: transparent;"
        ))

    def show_window(self):
        self._load()
        self.search.clear()
        self.search.setFocus()
        self._tab("all")
        s = QApplication.primaryScreen().geometry()
        self.move((s.width() - self.width()) // 2, (s.height() - self.height()) // 2)
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_window(self):
        self.hide()
        self.closed.emit()

    def _monitor(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._check)
        self.timer.start(1000)
        self._last = get_clipboard_text()

    def _check(self):
        c = get_clipboard_text()
        if c and c != self._last:
            if not any(h.get("content") == c for h in self.history):
                self.history.insert(0, {"content": c, "timestamp": datetime.now().isoformat(), "pinned": False})
                if len(self.history) > 500:
                    self.history = self.history[:500]
                save_history(self.history)
                if self.isVisible():
                    self._refresh()
            self._last = c

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Escape:
            self.hide()
        elif k == Qt.Key.Key_Down:
            if self.sel < len(self.filtered) - 1:
                self._select(self.sel + 1)
                self.scroll.ensureWidgetVisible(self.items[self.sel])
        elif k == Qt.Key.Key_Up:
            if self.sel > 0:
                self._select(self.sel - 1)
                self.scroll.ensureWidgetVisible(self.items[self.sel])
        elif k == Qt.Key.Key_PageDown:
            self._select(min(self.sel + 10, len(self.filtered) - 1))
        elif k == Qt.Key.Key_PageUp:
            self._select(max(self.sel - 10, 0))
        elif k == Qt.Key.Key_Home:
            self._select(0)
        elif k == Qt.Key.Key_End:
            self._select(max(0, len(self.filtered) - 1))
        else:
            super().keyPressEvent(e)


def main():
    ensure_dirs()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list":
            for i, item in enumerate(load_history()[:20]):
                print(f"{i+1:3d}. {item.get('content', '')[:60].replace(chr(10), ' ')}")
        elif cmd == "count":
            print(f"{len(load_history())} items")
        elif cmd == "clear":
            save_history([])
            print("Cleared")
        return

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(SURFACE))
    p.setColor(QPalette.ColorRole.WindowText, QColor(FG))
    p.setColor(QPalette.ColorRole.Base, QColor(BG))
    p.setColor(QPalette.ColorRole.Text, QColor(FG))
    app.setPalette(p)

    w = Window()
    w.show_window()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
