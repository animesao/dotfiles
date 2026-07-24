#!/usr/bin/env python3
"""
launcher — minimal app launcher for Wayland/niri
Search-first with "All" toggle. PyQt6 + Gruvbox theme.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QSize
from PyQt6.QtGui import (
    QColor, QKeySequence, QPainter, QShortcut,
    QPixmap, QIcon, QFont, QFontMetrics
)

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
BLUE     = "#83a598"

R = 12
R_SM = 8


# ─── Desktop file parser ───
def get_desktop_files() -> list:
    apps = []
    paths = [
        Path.home() / ".local" / "share" / "applications",
        Path("/usr/share/applications"),
        Path("/usr/local/share/applications"),
    ]
    for p in paths:
        if not p.exists():
            continue
        for f in p.glob("*.desktop"):
            try:
                content = f.read_text(errors="ignore")
                name = ""
                exec_cmd = ""
                icon = ""
                no_display = False
                in_entry = False

                for line in content.splitlines():
                    if line.startswith("[Desktop Entry]"):
                        in_entry = True
                        continue
                    if line.startswith("[") and in_entry:
                        break
                    if not in_entry:
                        continue

                    if line.startswith("Name=") and not name:
                        name = line.split("=", 1)[1].strip()
                    elif line.startswith("Exec=") and not exec_cmd:
                        exec_cmd = line.split("=", 1)[1].strip()
                    elif line.startswith("Icon=") and not icon:
                        icon = line.split("=", 1)[1].strip()
                    elif line.startswith("NoDisplay=true"):
                        no_display = True

                if name and exec_cmd and not no_display:
                    apps.append({
                        "name": name,
                        "exec": exec_cmd,
                        "icon": icon,
                        "file": str(f),
                    })
            except Exception:
                continue

    apps.sort(key=lambda x: x["name"].lower())
    return apps


def find_icon(icon_name: str) -> QIcon:
    if not icon_name:
        return QIcon()

    # Try icon theme
    icon = QIcon.fromTheme(icon_name)
    if icon.isNull():
        # Try full path
        for ext in ["", ".svg", ".png"]:
            p = Path(f"/usr/share/icons/hicolor/scalable/apps/{icon_name}{ext}")
            if p.exists():
                return QIcon(str(p))
            p = Path(f"/usr/share/pixmaps/{icon_name}{ext}")
            if p.exists():
                return QIcon(str(p))
    return icon


def run_app(exec_cmd: str):
    parts = exec_cmd.split()
    try:
        subprocess.Popen(parts, start_new_session=True)
    except Exception:
        pass


# ─── App Card ───
class AppCard(QWidget):
    def __init__(self, app, idx):
        super().__init__()
        self.app = app
        self._sel = False
        self._hov = False
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(8)

        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        icon = find_icon(app.get("icon", ""))
        if not icon.isNull():
            px = icon.pixmap(20, 20)
            self.icon_label.setPixmap(px)
        else:
            self.icon_label.setText(app["name"][0].upper())
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.icon_label.setFont(QFont("Adwaita Sans", 10, QFont.Weight.Bold))
            self.icon_label.setStyleSheet(f"color: {FG_DIM}; background: {SURF_HI}; border-radius: 10px;")
        lay.addWidget(self.icon_label)

        # Name
        self.label = QLabel(app["name"])
        self.label.setFont(QFont("Adwaita Sans", 11))
        self.label.setStyleSheet(f"color: {FG}; background: transparent;")
        lay.addWidget(self.label, 1)

        # Exec preview
        exec_short = app["exec"].split()[0].split("/")[-1]
        self.exec_label = QLabel(exec_short)
        self.exec_label.setFont(QFont("Adwaita Sans", 9))
        self.exec_label.setStyleSheet(f"color: {FG_FAINT}; background: transparent;")
        lay.addWidget(self.exec_label)

    def set_selected(self, s):
        self._sel = s
        self.update()

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


# ─── Window ───
class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.all_apps = []
        self.filtered = []
        self.items = []
        self.sel = 0
        self.show_all = False
        self._build()
        self._load()

    def _build(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 400)

        # Shadow
        sf = QFrame(self)
        sf.setGeometry(4, 4, 472, 392)
        e = QGraphicsDropShadowEffect()
        e.setBlurRadius(40)
        e.setOffset(0, 8)
        c = QColor(BG)
        c.setAlpha(200)
        e.setColor(c)
        sf.setGraphicsEffect(e)

        # Surface
        self.surf = QFrame(self)
        self.surf.setStyleSheet(f"QFrame {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: {R}px; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.surf)

        col = QVBoxLayout(self.surf)
        col.setContentsMargins(12, 10, 12, 10)
        col.setSpacing(8)

        # ─── Search bar ───
        sb = QFrame()
        sb.setStyleSheet(f"QFrame {{ background: {BG}; border: 1px solid {BORDER}; border-radius: {R_SM}px; }}")
        sl = QHBoxLayout(sb)
        sl.setContentsMargins(10, 0, 10, 0)
        sl.setSpacing(6)

        # Search icon
        si = QLabel()
        si.setText("🔍")
        si.setFont(QFont("Adwaita Sans", 12))
        si.setStyleSheet(f"color: {FG_FAINT}; background: transparent;")
        sl.addWidget(si)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Type to search...")
        self.search.setFont(QFont("Adwaita Sans", 13))
        self.search.setStyleSheet(f"""
            QLineEdit {{ background: transparent; color: {FG}; border: none; padding: 6px 0; }}
            QLineEdit::placeholder {{ color: {FG_FAINT}; }}
        """)
        self.search.textChanged.connect(self._filter)
        sl.addWidget(self.search, 1)

        col.addWidget(sb)

        # ─── Tabs: Search | All ───
        tabs = QHBoxLayout()
        tabs.setSpacing(4)

        self.tab_search = QPushButton("Search")
        self.tab_search.setCheckable(True)
        self.tab_search.setChecked(True)
        self.tab_search.setFixedHeight(24)
        self.tab_search.setFont(QFont("Adwaita Sans", 9, QFont.Weight.Bold))
        self.tab_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_search.clicked.connect(lambda: self._set_mode("search"))
        self._style_tab(self.tab_search, False)

        self.tab_all = QPushButton("All")
        self.tab_all.setCheckable(True)
        self.tab_all.setFixedHeight(24)
        self.tab_all.setFont(QFont("Adwaita Sans", 9, QFont.Weight.Bold))
        self.tab_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_all.clicked.connect(lambda: self._set_mode("all"))
        self._style_tab(self.tab_all, False)

        tabs.addWidget(self.tab_search)
        tabs.addWidget(self.tab_all)
        tabs.addStretch()

        # App count
        self.count = QLabel("0 apps")
        self.count.setFont(QFont("Adwaita Sans", 9))
        self.count.setStyleSheet(f"color: {FG_FAINT}; background: transparent;")
        tabs.addWidget(self.count)

        col.addLayout(tabs)

        # ─── App list ───
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: transparent; width: 4px; }}
            QScrollBar::handle:vertical {{ background: {HOVER}; border-radius: 2px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {FG_FAINT}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self.list_w = QWidget()
        self.list_w.setStyleSheet("background: transparent;")
        self.list_lay = QVBoxLayout(self.list_w)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(1)
        self.list_lay.addStretch()

        self.scroll.setWidget(self.list_w)
        col.addWidget(self.scroll, 1)

        # ─── Shortcuts ───
        QShortcut(QKeySequence("Return"), self, self._launch)
        QShortcut(QKeySequence("Escape"), self, self.hide)
        QShortcut(QKeySequence("Down"), self, self._down)
        QShortcut(QKeySequence("Up"), self, self._up)
        QShortcut(QKeySequence("Tab"), self, self._toggle_mode)

    def _style_tab(self, btn, active):
        if active:
            btn.setStyleSheet(f"QPushButton {{ background: {GREEN}; color: {BG}; border: none; border-radius: 12px; padding: 0 16px; }}")
        else:
            btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {FG_DIM}; border: none; border-radius: 12px; padding: 0 16px; }} QPushButton:hover {{ color: {FG}; }}")

    def _set_mode(self, mode):
        self.show_all = (mode == "all")
        self.tab_search.setChecked(mode == "search")
        self.tab_all.setChecked(mode == "all")
        self._style_tab(self.tab_search, mode == "search")
        self._style_tab(self.tab_all, mode == "all")
        self._filter()

    def _toggle_mode(self):
        if self.show_all:
            self._set_mode("search")
        else:
            self._set_mode("all")

    def _load(self):
        self.all_apps = get_desktop_files()
        self._filter()

    def _filter(self):
        for w in self.items:
            w.setParent(None)
            w.deleteLater()
        self.items.clear()

        q = self.search.text().lower().strip()
        self.filtered = []
        idx = 0

        for app in self.all_apps:
            if self.show_all:
                # Show all apps, sorted by name
                pass
            else:
                # Search mode: only show matches
                if not q:
                    continue
                if q not in app["name"].lower():
                    continue

            w = AppCard(app, idx)
            w.mousePressEvent = lambda e, i=idx: self._sel(i)
            w.mouseDoubleClickEvent = lambda e, i=idx: (self._sel(i), self._launch())
            self.list_lay.insertWidget(self.list_lay.count() - 1, w)
            self.items.append(w)
            self.filtered.append(app)
            idx += 1

        self.count.setText(f"{len(self.items)} apps")
        if self.items:
            self._sel(0)

    def _sel(self, i):
        self.sel = min(i, len(self.items) - 1)
        for j, w in enumerate(self.items):
            w.set_selected(j == self.sel)
        # Scroll to selected
        if self.items and 0 <= self.sel < len(self.items):
            self.scroll.ensureWidgetVisible(self.items[self.sel])

    def _down(self):
        if self.sel < len(self.items) - 1:
            self._sel(self.sel + 1)

    def _up(self):
        if self.sel > 0:
            self._sel(self.sel - 1)

    def _launch(self):
        if self.sel < len(self.filtered):
            app = self.filtered[self.sel]
            run_app(app["exec"])
            self.hide()

    def show_launcher(self):
        self.search.clear()
        self._set_mode("search")
        self._load()
        self.search.setFocus()
        s = QApplication.primaryScreen().geometry()
        self.move((s.width() - self.width()) // 2, (s.height() - self.height()) // 2)
        self.show()
        self.raise_()
        self.activateWindow()

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


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    p = app.palette()
    p.setColor(p.ColorRole.Window, QColor(SURFACE))
    p.setColor(p.ColorRole.WindowText, QColor(FG))
    p.setColor(p.ColorRole.Base, QColor(BG))
    p.setColor(p.ColorRole.Text, QColor(FG))
    app.setPalette(p)

    launcher = Launcher()
    launcher.show_launcher()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
