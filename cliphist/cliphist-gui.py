#!/usr/bin/env python3
"""
cliphist — clipboard history manager for Wayland
Full-featured: SQLite, image preview with zoom, search, pin, Gruvbox dark theme.
"""

import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect, QScrollArea,
    QSplitter, QMenu, QSystemTrayIcon,
    QSpinBox, QCheckBox, QComboBox, QDialog,
    QFormLayout, QMessageBox, QAbstractItemView,
    QToolButton, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QTimer, QRectF, QSize, QThread,
    pyqtSignal, QSettings, QPoint
)
from PyQt6.QtGui import (
    QColor, QKeySequence, QPainter, QShortcut,
    QPalette, QPixmap, QIcon, QFont, QFontMetrics,
    QAction, QCursor, QImage, QTransform
)

# ─── Paths ───
DATA_DIR = Path.home() / ".local" / "share" / "cliphist"
DB_FILE = DATA_DIR / "history.db"
CONFIG_FILE = Path.home() / ".config" / "cliphist" / "config.json"

# ─── Gruvbox Dark ───
class C:
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
    BLUE     = "#83a598"
    PURPLE   = "#d3869b"

R = 14
R_SM = 8


# ─── Database ───
class Database:
    def __init__(self, path: Path):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS clipboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'text',
                is_pinned INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                copied_count INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def add(self, content: str, content_type: str = "text") -> bool:
        if not content or not content.strip():
            return False
        cur = self.conn.execute(
            "SELECT id FROM clipboard WHERE content = ?", (content,))
        if cur.fetchone():
            self.conn.execute(
                "UPDATE clipboard SET created_at = datetime('now', 'localtime'), "
                "copied_count = copied_count + 1 WHERE content = ?", (content,))
            self.conn.commit()
            return False
        self.conn.execute(
            "INSERT INTO clipboard (content, content_type) VALUES (?, ?)",
            (content, content_type))
        self.conn.commit()
        self._trim()
        return True

    def _trim(self, max_items: int = 500):
        self.conn.execute("""
            DELETE FROM clipboard WHERE id NOT IN (
                SELECT id FROM clipboard WHERE is_pinned = 1
                ORDER BY created_at DESC LIMIT ?
            ) AND is_pinned = 0
        """, (max_items,))
        self.conn.commit()

    def get_all(self) -> list[dict]:
        cur = self.conn.execute(
            "SELECT id, content, content_type, is_pinned, created_at, copied_count "
            "FROM clipboard ORDER BY is_pinned DESC, created_at DESC")
        return [{"id": r[0], "content": r[1], "type": r[2],
                 "pinned": bool(r[3]), "date": r[4], "copies": r[5]}
                for r in cur.fetchall()]

    def search(self, query: str) -> list[dict]:
        cur = self.conn.execute(
            "SELECT id, content, content_type, is_pinned, created_at, copied_count "
            "FROM clipboard WHERE content LIKE ? "
            "ORDER BY is_pinned DESC, created_at DESC",
            (f"%{query}%",))
        return [{"id": r[0], "content": r[1], "type": r[2],
                 "pinned": bool(r[3]), "date": r[4], "copies": r[5]}
                for r in cur.fetchall()]

    def toggle_pin(self, item_id: int):
        self.conn.execute(
            "UPDATE clipboard SET is_pinned = NOT is_pinned WHERE id = ?",
            (item_id,))
        self.conn.commit()

    def delete(self, item_id: int):
        self.conn.execute("DELETE FROM clipboard WHERE id = ?", (item_id,))
        self.conn.commit()

    def clear(self):
        self.conn.execute("DELETE FROM clipboard WHERE is_pinned = 0")
        self.conn.commit()

    def get_by_id(self, item_id: int) -> dict | None:
        cur = self.conn.execute(
            "SELECT id, content, content_type, is_pinned, created_at, copied_count "
            "FROM clipboard WHERE id = ?", (item_id,))
        r = cur.fetchone()
        if r:
            return {"id": r[0], "content": r[1], "type": r[2],
                    "pinned": bool(r[3]), "date": r[4], "copies": r[5]}
        return None

    def increment_copy(self, item_id: int):
        self.conn.execute(
            "UPDATE clipboard SET copied_count = copied_count + 1 WHERE id = ?",
            (item_id,))
        self.conn.commit()


# ─── Clipboard monitor ───
class ClipboardMonitor(QThread):
    changed = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._running = True
        self._last_text = ""
        self._last_image_hash = ""

    def run(self):
        while self._running:
            time.sleep(0.5)
            text = self._get_text()
            if text and text != self._last_text:
                self._last_text = text
                self.changed.emit(text, "text")
                continue
            img_hash = self._get_image_hash()
            if img_hash and img_hash != self._last_image_hash:
                self._last_image_hash = img_hash
                img_path = self._save_image()
                if img_path:
                    self.changed.emit(f"[image:{img_path}]", "image")

    def _get_text(self) -> str:
        try:
            r = subprocess.run(["wl-paste", "-t", "text/plain"],
                               capture_output=True, text=True, timeout=2)
            return r.stdout if r.returncode == 0 else ""
        except Exception:
            return ""

    def _get_image_hash(self) -> str:
        try:
            import hashlib
            r = subprocess.run(["wl-paste", "-t", "image/png"],
                               capture_output=True, timeout=2)
            if r.returncode == 0 and len(r.stdout) > 100:
                return hashlib.md5(r.stdout).hexdigest()[:12]
        except Exception:
            pass
        return ""

    def _save_image(self) -> str | None:
        try:
            import hashlib
            img_dir = DATA_DIR / "images"
            img_dir.mkdir(exist_ok=True)
            r = subprocess.run(["wl-paste", "-t", "image/png"],
                               capture_output=True, timeout=2)
            if r.returncode == 0 and len(r.stdout) > 100:
                h = hashlib.md5(r.stdout).hexdigest()[:12]
                path = img_dir / f"{h}.png"
                if not path.exists():
                    path.write_bytes(r.stdout)
                return str(path)
        except Exception:
            pass
        return None

    def stop(self):
        self._running = False
        self.wait()


# ─── SVG Icons ───
def _svg(svg, color, size=16):
    tag = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
           f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
           f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
           f'{svg}</svg>')
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    px.loadFromData(tag.encode())
    return QIcon(px)


class I:
    SEARCH  = lambda c=C.FG_DIM: _svg('<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/>', c)
    COPY    = lambda c=C.FG_DIM: _svg('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 012-2h10"/>', c)
    PIN     = lambda c=C.FG_DIM: _svg('<path d="M12 17v5"/><path d="M9 11l3-7 3 7"/><circle cx="12" cy="9" r="3"/><path d="M5 21h14"/>', c)
    TRASH   = lambda c=C.FG_DIM: _svg('<path d="M3 6h18"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/><path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/>', c)
    CLOSE   = lambda c=C.FG_DIM: _svg('<path d="M18 6L6 18"/><path d="M6 6l12 12"/>', c)
    ZOOM_IN = lambda c=C.FG_DIM: _svg('<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/><path d="M11 8v6"/><path d="M8 11h6"/>', c)
    ZOOM_OUT= lambda c=C.FG_DIM: _svg('<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/><path d="M8 11h6"/>', c)
    CLEAR   = lambda c=C.FG_DIM: _svg('<path d="M20 20H9L3 14a1 1 0 010-1.4l8.6-8.6a2 2 0 012.8 0l5.6 5.6a2 2 0 010 2.8L15 20"/>', c)
    SETTINGS= lambda c=C.FG_DIM: _svg('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>', c)


# ─── History row ───
class HistoryRow(QWidget):
    def __init__(self, item: dict, idx: int):
        super().__init__()
        self.item = item
        self._sel = False
        self._hov = False
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(10)

        # thumbnail / icon
        thumb = QLabel()
        thumb.setFixedSize(28, 28)
        thumb.setStyleSheet(f"background:{C.SURF_HI}; border-radius:6px;")
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if item["type"] == "image":
            img_path = item["content"].replace("[image:", "").replace("]", "")
            if os.path.exists(img_path):
                px = QPixmap(img_path).scaled(28, 28,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                thumb.setPixmap(px)
            else:
                thumb.setText("📷")
                thumb.setFont(QFont("Adwaita Sans", 12))
        else:
            letter = item["content"][0].upper() if item["content"] else "?"
            colors = [C.GREEN, C.YELLOW, C.AQUA, C.BLUE, C.PURPLE]
            c = colors[ord(letter) % len(colors)]
            thumb.setText(letter)
            thumb.setFont(QFont("Adwaita Sans", 10, QFont.Weight.Bold))
            thumb.setStyleSheet(f"color:{C.BG}; background:{c}; border-radius:6px;")
        lay.addWidget(thumb)

        # text
        col = QVBoxLayout()
        col.setSpacing(0)
        col.setContentsMargins(0, 0, 0, 0)

        if item["type"] == "image":
            name = QLabel("Image")
            name.setStyleSheet(f"color:{C.AQUA}; background:transparent;")
        else:
            text = item["content"].replace("\n", " ").replace("\r", "")
            text = text[:60] + "…" if len(text) > 60 else text
            name = QLabel(text)
            name.setStyleSheet(f"color:{C.FG}; background:transparent;")
        name.setFont(QFont("Adwaita Sans", 10, QFont.Weight.DemiBold))
        col.addWidget(name)

        # meta line
        meta_parts = []
        if item.get("date"):
            try:
                dt = datetime.fromisoformat(item["date"])
                now = datetime.now()
                meta_parts.append(dt.strftime("%H:%M") if dt.date() == now.date()
                                  else dt.strftime("%d %b"))
            except ValueError:
                pass
        if item.get("copies", 0) > 0:
            meta_parts.append(f"×{item['copies']}")
        meta = QLabel("  ".join(meta_parts))
        meta.setFont(QFont("Adwaita Sans", 8))
        meta.setStyleSheet(f"color:{C.FG_FAINT}; background:transparent;")
        col.addWidget(meta)

        lay.addLayout(col, 1)

        # pin badge
        if item.get("pinned"):
            pin = QLabel("★")
            pin.setFont(QFont("Adwaita Sans", 10))
            pin.setStyleSheet(f"color:{C.YELLOW}; background:transparent;")
            lay.addWidget(pin)

    def set_selected(self, s: bool):
        self._sel = s
        self.update()

    def paintEvent(self, e):
        if self._sel or self._hov:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(C.GREEN if self._sel else C.HOVER))
            p.setOpacity(0.25 if self._sel else 0.35)
            p.drawRoundedRect(QRectF(self.rect()), R_SM, R_SM)
            p.end()

    def enterEvent(self, e):
        self._hov = True
        self.update()

    def leaveEvent(self, e):
        self._hov = False
        self.update()


# ─── Image viewer dialog ───
class ImageViewer(QDialog):
    def __init__(self, img_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Preview")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(f"background:{C.BG};")

        self._zoom = 1.0
        self._path = img_path

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(12, 8, 12, 8)
        toolbar.setSpacing(6)

        btn_out = QPushButton()
        btn_out.setIcon(I.ZOOM_OUT(C.FG_DIM))
        btn_out.setIconSize(QSize(16, 16))
        btn_out.setFixedSize(30, 30)
        btn_out.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_out.setStyleSheet(f"QPushButton{{background:{C.SURF_HI};border:none;border-radius:6px;}}"
                              f"QPushButton:hover{{background:{C.HOVER};}}")
        btn_out.clicked.connect(lambda: self._zoom_by(-0.25))
        toolbar.addWidget(btn_out)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFont(QFont("Adwaita Sans", 9))
        self.zoom_label.setStyleSheet(f"color:{C.FG_DIM}; background:transparent;")
        self.zoom_label.setFixedWidth(40)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self.zoom_label)

        btn_in = QPushButton()
        btn_in.setIcon(I.ZOOM_IN(C.FG_DIM))
        btn_in.setIconSize(QSize(16, 16))
        btn_in.setFixedSize(30, 30)
        btn_in.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_in.setStyleSheet(f"QPushButton{{background:{C.SURF_HI};border:none;border-radius:6px;}}"
                             f"QPushButton:hover{{background:{C.HOVER};}}")
        btn_in.clicked.connect(lambda: self._zoom_by(0.25))
        toolbar.addWidget(btn_in)

        btn_fit = QPushButton("Fit")
        btn_fit.setFont(QFont("Adwaita Sans", 9, QFont.Weight.Bold))
        btn_fit.setFixedHeight(30)
        btn_fit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fit.setStyleSheet(f"QPushButton{{background:{C.SURF_HI};color:{C.FG_DIM};border:none;"
                              f"border-radius:6px;padding:0 12px;}}"
                              f"QPushButton:hover{{background:{C.HOVER};color:{C.FG};}}")
        btn_fit.clicked.connect(self._fit)
        toolbar.addWidget(btn_fit)

        toolbar.addStretch()

        btn_close = QPushButton()
        btn_close.setIcon(I.CLOSE(C.FG_DIM))
        btn_close.setIconSize(QSize(16, 16))
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:6px;}}"
                                f"QPushButton:hover{{background:{C.RED};}}")
        btn_close.clicked.connect(self.close)
        toolbar.addWidget(btn_close)

        lay.addLayout(toolbar)

        # image area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea{{background:{C.BG};border:none;}}")

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet(f"background:{C.BG};")

        self._original = QPixmap(img_path)
        self._update_image()

        scroll.setWidget(self.img_label)
        lay.addWidget(scroll, 1)

        # filename
        fname = QLabel(os.path.basename(img_path))
        fname.setFont(QFont("Adwaita Sans", 8))
        fname.setStyleSheet(f"color:{C.FG_FAINT}; background:transparent; padding:6px;")
        lay.addWidget(fname)

    def _zoom_by(self, delta):
        self._zoom = max(0.1, min(5.0, self._zoom + delta))
        self._update_image()

    def _fit(self):
        if self._original.isNull():
            return
        pw = self.width() - 40
        ph = self.height() - 80
        self._zoom = min(pw / self._original.width(),
                         ph / self._original.height(), 1.0)
        self._update_image()

    def _update_image(self):
        if self._original.isNull():
            return
        scaled = self._original.scaled(
            int(self._original.width() * self._zoom),
            int(self._original.height() * self._zoom),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self.img_label.setPixmap(scaled)
        self.zoom_label.setText(f"{int(self._zoom * 100)}%")


# ─── Settings dialog ───
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(350, 250)
        self.setStyleSheet(f"background:{C.SURFACE}; color:{C.FG};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        title = QLabel("Settings")
        title.setFont(QFont("Adwaita Sans", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{C.FG}; background:transparent;")
        lay.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)

        self.max_items = QSpinBox()
        self.max_items.setRange(50, 5000)
        self.max_items.setValue(500)
        self.max_items.setFixedHeight(28)
        self.max_items.setStyleSheet(f"background:{C.BG}; color:{C.FG}; border:1px solid {C.BORDER};"
                                     f"border-radius:6px; padding:0 8px;")
        form.addRow("Max items:", self.max_items)

        self.auto_copy = QCheckBox("Auto-copy on select")
        self.auto_copy.setChecked(True)
        self.auto_copy.setStyleSheet(f"color:{C.FG}; background:transparent;")
        form.addRow(self.auto_copy)

        self.notifications = QCheckBox("Show notifications")
        self.notifications.setChecked(True)
        self.notifications.setStyleSheet(f"color:{C.FG}; background:transparent;")
        form.addRow(self.notifications)

        lay.addLayout(form)
        lay.addStretch()

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setFixedSize(80, 28)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet(f"QPushButton{{background:{C.SURF_HI};color:{C.FG_DIM};border:none;"
                             f"border-radius:6px;}} QPushButton:hover{{background:{C.HOVER};color:{C.FG};}}")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)

        save = QPushButton("Save")
        save.setFixedSize(80, 28)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.setStyleSheet(f"QPushButton{{background:{C.GREEN};color:{C.BG};border:none;"
                           f"border-radius:6px;font-weight:bold;}} "
                           f"QPushButton:hover{{background:{C.YELLOW};}}")
        save.clicked.connect(self.accept)
        btns.addWidget(save)
        lay.addLayout(btns)


# ─── Main window ───
class ClipHistGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database(DB_FILE)
        self.items = []
        self.rows = []
        self.sel = 0
        self.monitor = ClipboardMonitor()
        self.monitor.changed.connect(self._on_clip_change)
        self._build()
        self._load()

    def _build(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(520, 480)

        # shadow
        shadow = QFrame(self)
        shadow.setGeometry(4, 4, 512, 472)
        eff = QGraphicsDropShadowEffect()
        eff.setBlurRadius(50)
        eff.setOffset(0, 10)
        c = QColor(C.BG); c.setAlpha(180)
        eff.setColor(c)
        shadow.setGraphicsEffect(eff)

        # surface
        surf = QFrame(self)
        surf.setStyleSheet(f"QFrame{{background:{C.SURFACE};border:1px solid {C.BORDER};"
                           f"border-radius:{R}px;}}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(surf)

        col = QVBoxLayout(surf)
        col.setContentsMargins(14, 12, 14, 12)
        col.setSpacing(10)

        # ── header ──
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background:{C.GREEN};border-radius:4px;")
        hdr.addWidget(dot)
        title = QLabel("Clipboard")
        title.setFont(QFont("Adwaita Sans", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{C.FG};background:transparent;")
        hdr.addWidget(title)
        hdr.addStretch()

        self.count = QLabel("0")
        self.count.setFont(QFont("Adwaita Sans", 11))
        self.count.setStyleSheet(f"color:{C.FG_FAINT};background:transparent;")
        hdr.addWidget(self.count)

        # settings btn
        btn_set = QPushButton()
        btn_set.setIcon(I.SETTINGS(C.FG_FAINT))
        btn_set.setIconSize(QSize(14, 14))
        btn_set.setFixedSize(26, 26)
        btn_set.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_set.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:13px;}}"
                              f"QPushButton:hover{{background:{C.HOVER};}}")
        btn_set.clicked.connect(self._settings)
        hdr.addWidget(btn_set)

        # close btn
        btn_close = QPushButton()
        btn_close.setIcon(I.CLOSE(C.FG_FAINT))
        btn_close.setIconSize(QSize(14, 14))
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:13px;}}"
                                f"QPushButton:hover{{background:{C.RED};}}")
        btn_close.clicked.connect(self.hide)
        hdr.addWidget(btn_close)

        col.addLayout(hdr)

        # ── search ──
        bar = QFrame()
        bar.setStyleSheet(f"QFrame{{background:{C.BG};border:1px solid {C.BORDER};border-radius:10px;}}")
        blay = QHBoxLayout(bar)
        blay.setContentsMargins(12, 0, 12, 0)
        blay.setSpacing(8)

        si = QLabel()
        si.setPixmap(I.SEARCH(C.FG_FAINT).pixmap(16, 16))
        blay.addWidget(si)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search clipboard...")
        self.search.setFont(QFont("Adwaita Sans", 13))
        self.search.setStyleSheet(
            f"QLineEdit{{background:transparent;color:{C.FG};border:none;padding:8px 0;"
            f"selection-background-color:{C.GREEN};selection-color:{C.BG};}}"
            f"QLineEdit::placeholder{{color:{C.FG_FAINT};}}")
        self.search.textChanged.connect(self._filter)
        blay.addWidget(self.search, 1)
        col.addWidget(bar)

        # ── actions bar ──
        acts = QHBoxLayout()
        acts.setSpacing(4)

        def mk_act(text, icon_fn, color, slot):
            b = QPushButton()
            b.setIcon(icon_fn(color))
            b.setIconSize(QSize(13, 13))
            b.setText(f" {text}")
            b.setFont(QFont("Adwaita Sans", 9, QFont.Weight.Bold))
            b.setFixedHeight(26)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:transparent;color:{color};border:1px solid {color}30;"
                f"border-radius:13px;padding:0 10px;}}"
                f"QPushButton:hover{{background:{color}15;border:1px solid {color}50;}}")
            b.clicked.connect(slot)
            acts.addWidget(b)

        mk_act("Copy", I.COPY, C.GREEN, self._copy)
        mk_act("Pin", I.PIN, C.YELLOW, self._pin)
        mk_act("Delete", I.TRASH, C.RED, self._delete)
        acts.addStretch()
        mk_act("Clear", I.CLEAR, C.FG_FAINT, self._clear)
        col.addLayout(acts)

        # ── divider ──
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{C.BORDER};")
        col.addWidget(div)

        # ── list ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea{{background:transparent;border:none;}}"
            f"QScrollBar:vertical{{background:transparent;width:5px;margin:4px 0;}}"
            f"QScrollBar::handle:vertical{{background:{C.HOVER};border-radius:2px;min-height:40px;}}"
            f"QScrollBar::handle:vertical:hover{{background:{C.FG_FAINT};}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}"
            f"QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:none;}}")

        list_w = QWidget()
        list_w.setStyleSheet("background:transparent;")
        self.list_lay = QVBoxLayout(list_w)
        self.list_lay.setContentsMargins(0, 4, 0, 0)
        self.list_lay.setSpacing(2)
        self.list_lay.addStretch()

        scroll.setWidget(list_w)
        col.addWidget(scroll, 1)

        # ── footer ──
        foot = QHBoxLayout()
        foot.setSpacing(16)
        for key, desc in [("Enter", "copy"), ("↓↑", "nav"),
                          ("Del", "delete"), ("Esc", "close")]:
            l = QLabel(f"{key} {desc}")
            l.setFont(QFont("Adwaita Sans", 8))
            l.setStyleSheet(f"color:{C.FG_FAINT};background:transparent;")
            foot.addWidget(l)
        foot.addStretch()
        col.addLayout(foot)

        # ── shortcuts ──
        QShortcut(QKeySequence("Return"), self, self._copy)
        QShortcut(QKeySequence("Escape"), self, self.hide)
        QShortcut(QKeySequence("Down"), self, self._down)
        QShortcut(QKeySequence("Up"), self, self._up)
        QShortcut(QKeySequence("Delete"), self, self._delete)
        QShortcut(QKeySequence("p"), self, self._pin)
        QShortcut(QKeySequence("/"), self, lambda: self.search.setFocus())

    def _load(self):
        self.items = self.db.get_all()
        self._render()

    def _filter(self):
        q = self.search.text().strip()
        self.items = self.db.search(q) if q else self.db.get_all()
        self._render()

    def _render(self):
        for w in self.rows:
            w.setParent(None)
            w.deleteLater()
        self.rows.clear()

        for idx, item in enumerate(self.items):
            row = HistoryRow(item, idx)
            row.mousePressEvent = lambda e, i=idx: self._select(i)
            row.mouseDoubleClickEvent = lambda e, i=idx: (
                self._select(i), self._copy())
            self.list_lay.insertWidget(self.list_lay.count() - 1, row)
            self.rows.append(row)

        self.count.setText(str(len(self.rows)))
        if self.rows:
            self._select(0)

    def _select(self, i: int):
        self.sel = min(max(i, 0), len(self.rows) - 1)
        for j, r in enumerate(self.rows):
            r.set_selected(j == self.sel)

    def _down(self):
        if self.sel < len(self.rows) - 1:
            self._select(self.sel + 1)

    def _up(self):
        if self.sel > 0:
            self._select(self.sel - 1)

    def _copy(self):
        if self.sel >= len(self.items):
            return
        item = self.items[self.sel]
        content = item["content"]

        if content.startswith("[image:"):
            img_path = content.replace("[image:", "").replace("]", "")
            if os.path.exists(img_path):
                try:
                    data = Path(img_path).read_bytes()
                    proc = subprocess.Popen(["wl-copy", "-t", "image/png"],
                                            stdin=subprocess.PIPE)
                    proc.communicate(input=data)
                except Exception:
                    pass
        else:
            try:
                subprocess.run(["wl-copy", "-t", "text/plain"],
                               input=content.encode(), check=True, timeout=2)
            except Exception:
                pass

        self.db.increment_copy(item["id"])
        self._flash("Copied", C.GREEN)
        QTimer.singleShot(200, self.hide)

    def _pin(self):
        if self.sel >= len(self.items):
            return
        item = self.items[self.sel]
        self.db.toggle_pin(item["id"])
        self._load()
        self._flash("Pinned" if not item.get("pinned") else "Unpinned", C.YELLOW)

    def _delete(self):
        if self.sel >= len(self.items):
            return
        item = self.items[self.sel]
        self.db.delete(item["id"])
        self._load()
        self._flash("Deleted", C.RED)

    def _clear(self):
        self.db.clear()
        self._load()
        self._flash("Cleared", C.FG_FAINT)

    def _flash(self, msg, color):
        self.count.setText(msg)
        self.count.setStyleSheet(f"color:{color};font-weight:bold;background:transparent;")
        QTimer.singleShot(1500, lambda: self.count.setStyleSheet(
            f"color:{C.FG_FAINT};background:transparent;"))
        QTimer.singleShot(1500, lambda: self.count.setText(str(len(self.rows))))

    def _settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            pass

    def _on_clip_change(self, content: str, content_type: str):
        self.db.add(content, content_type)
        if self.isVisible():
            self._load()

    def open_gui(self):
        self._load()
        self.search.clear()
        self.search.setFocus()
        s = QApplication.primaryScreen().geometry()
        self.move((s.width() - self.width()) // 2,
                  (s.height() - self.height()) // 2)
        self.show()
        self.raise_()
        self.activateWindow()
        if not self.monitor.isRunning():
            self.monitor.start()

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Down:
            self._down()
        elif k == Qt.Key.Key_Up:
            self._up()
        elif k == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(e)


# ─── CLI ───
def cli():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        db = Database(DB_FILE)
        if cmd == "list":
            for i, item in enumerate(db.get_all()[:20]):
                content = item["content"][:60].replace("\n", " ")
                print(f"{i+1:3d}. {content}")
        elif cmd == "count":
            print(f"{len(db.get_all())} items")
        elif cmd == "clear":
            db.clear()
            print("Cleared")
        elif cmd == "daemon":
            print("Daemon mode — use cliphist-gui for clipboard monitoring")
        return


def main():
    cli()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    p = app.palette()
    p.setColor(p.ColorRole.Window, QColor(C.SURFACE))
    p.setColor(p.ColorRole.WindowText, QColor(C.FG))
    p.setColor(p.ColorRole.Base, QColor(C.BG))
    p.setColor(p.ColorRole.Text, QColor(C.FG))
    app.setPalette(p)

    w = ClipHistGUI()
    w.open_gui()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
