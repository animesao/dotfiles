#!/usr/bin/env python3
"""
launcher — minimal app launcher for Wayland/niri
Search-first with "All" toggle. PyQt6 + Gruvbox theme.
"""

import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect, QScrollArea
)
from PyQt6.QtCore import Qt, QRectF, QSize
from PyQt6.QtGui import (
    QColor, QKeySequence, QPainter, QShortcut,
    QPixmap, QIcon, QFont
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
PURPLE   = "#d3869b"

R = 14
R_SM = 8


# ─── SVG Icons ───
def mk_icon(svg, color, size=16):
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{svg}</svg>'
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    px.loadFromData(s.encode())
    return QIcon(px)


class I:
    @staticmethod
    def search(c=FG_DIM):
        return mk_icon('<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/>', c)

    @staticmethod
    def grid(c=FG_DIM):
        return mk_icon('<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>', c)

    @staticmethod
    def launch(c=FG_DIM):
        return mk_icon('<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>', c)

    @staticmethod
    def terminal(c=FG_DIM):
        return mk_icon('<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>', c)

    @staticmethod
    def folder(c=FG_DIM):
        return mk_icon('<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>', c)

    @staticmethod
    def settings(c=FG_DIM):
        return mk_icon('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>', c)


def load_icon(icon_name: str, size: int = 22) -> QPixmap:
    """Load app icon from system theme."""
    icon = QIcon.fromTheme(icon_name)
    if not icon.isNull():
        return icon.pixmap(size, size)

    for base in [
        Path.home() / ".local/share/icons",
        Path("/usr/share/icons/hicolor/scalable/apps"),
        Path("/usr/share/icons/hicolor/48x48/apps"),
        Path("/usr/share/pixmaps"),
    ]:
        for ext in [".svg", ".png", ".xpm", ""]:
            p = base / f"{icon_name}{ext}"
            if p.exists():
                return QPixmap(str(p)).scaled(
                    size, size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

    return QPixmap()


def run_app(exec_cmd: str):
    try:
        subprocess.Popen(exec_cmd.split(), start_new_session=True)
    except Exception:
        pass


# ─── Desktop file parser ───
def get_desktop_files() -> list:
    apps = []
    paths = [
        Path.home() / ".local" / "share" / "applications",
        Path("/usr/share/applications"),
    ]
    for p in paths:
        if not p.exists():
            continue
        for f in p.glob("*.desktop"):
            try:
                content = f.read_text(errors="ignore")
                name = exec_cmd = icon = ""
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
                    apps.append({"name": name, "exec": exec_cmd, "icon": icon})
            except Exception:
                continue

    apps.sort(key=lambda x: x["name"].lower())
    return apps


# ─── App Card ───
class AppCard(QWidget):
    def __init__(self, app, idx, total):
        super().__init__()
        self.app = app
        self._sel = False
        self._hov = False
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(10)

        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(28, 28)
        px = load_icon(app.get("icon", ""), 28)
        if not px.isNull():
            self.icon_label.setPixmap(px)
        else:
            # Fallback: letter circle
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.icon_label.setFont(QFont("Adwaita Sans", 11, QFont.Weight.Bold))
            letter = app["name"][0].upper()
            colors = [GREEN, YELLOW, AQUA, BLUE, PURPLE]
            c = colors[ord(letter) % len(colors)]
            self.icon_label.setText(letter)
            self.icon_label.setStyleSheet(
                f"color: {BG}; background: {c}; border-radius: 14px;"
            )
        lay.addWidget(self.icon_label)

        # Name + exec
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        text_col.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(app["name"])
        self.label.setFont(QFont("Adwaita Sans", 11, QFont.Weight.DemiBold))
        self.label.setStyleSheet(f"color: {FG}; background: transparent;")
        text_col.addWidget(self.label)

        exec_short = app["exec"].split()[0].split("/")[-1]
        self.exec_label = QLabel(exec_short)
        self.exec_label.setFont(QFont("Adwaita Sans", 8))
        self.exec_label.setStyleSheet(f"color: {FG_FAINT}; background: transparent;")
        text_col.addWidget(self.exec_label)

        lay.addLayout(text_col, 1)

        # Index badge
        if total <= 10:
            self.idx_label = QLabel(str(idx + 1))
            self.idx_label.setFixedSize(20, 20)
            self.idx_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.idx_label.setFont(QFont("Adwaita Sans", 8, QFont.Weight.Bold))
            self.idx_label.setStyleSheet(
                f"color: {FG_FAINT}; background: {SURF_HI}; border-radius: 10px;"
            )
            lay.addWidget(self.idx_label)

    def set_selected(self, s):
        self._sel = s
        if hasattr(self, "idx_label"):
            if s:
                self.idx_label.setStyleSheet(
                    f"color: {BG}; background: {GREEN}; border-radius: 10px;"
                )
            else:
                self.idx_label.setStyleSheet(
                    f"color: {FG_FAINT}; background: {SURF_HI}; border-radius: 10px;"
                )
        self.update()

    def paintEvent(self, e):
        if self._sel or self._hov:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor(GREEN if self._sel else HOVER))
            p.setPen(Qt.PenStyle.NoPen)
            alpha = 40 if self._sel else 25
            p.setBrush(QColor(GREEN if self._sel else HOVER))
            p.drawRoundedRect(QRectF(self.rect()), R_SM, R_SM)
            p.end()

    def enterEvent(self, e):
        self._hov = True
        self.update()

    def leaveEvent(self, e):
        self._hov = False
        self.update()


# ─── Pill Tab ───
class Pill(QPushButton):
    def __init__(self, text, icon):
        super().__init__()
        self._active = False
        self.setText(f"  {text}")
        self.setIcon(icon)
        self.setIconSize(QSize(12, 12))
        self.setCheckable(True)
        self.setFixedHeight(26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Adwaita Sans", 9, QFont.Weight.Bold))
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {GREEN};
                    color: {BG};
                    border: none;
                    border-radius: 13px;
                    padding: 0 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {FG_DIM};
                    border: none;
                    border-radius: 13px;
                    padding: 0 14px;
                }}
                QPushButton:hover {{
                    color: {FG};
                    background: {HOVER};
                }}
            """)

    def set_active(self, a):
        self._active = a
        self.setChecked(a)
        self._update_style()


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
        self.setFixedSize(500, 440)

        # Shadow frame
        sf = QFrame(self)
        sf.setGeometry(4, 4, 492, 432)
        e = QGraphicsDropShadowEffect()
        e.setBlurRadius(50)
        e.setOffset(0, 10)
        c = QColor(BG)
        c.setAlpha(180)
        e.setColor(c)
        sf.setGraphicsEffect(e)

        # Surface
        self.surf = QFrame(self)
        self.surf.setStyleSheet(
            f"QFrame {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: {R}px; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.surf)

        col = QVBoxLayout(self.surf)
        col.setContentsMargins(14, 12, 14, 12)
        col.setSpacing(10)

        # ─── Header ───
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {GREEN}; border-radius: 4px;")
        hdr.addWidget(dot)

        title = QLabel("Launcher")
        title.setFont(QFont("Adwaita Sans", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {FG}; background: transparent;")
        hdr.addWidget(title)

        hdr.addStretch()

        self.count = QLabel("0")
        self.count.setFont(QFont("Adwaita Sans", 11))
        self.count.setStyleSheet(f"color: {FG_FAINT}; background: transparent;")
        hdr.addWidget(self.count)

        col.addLayout(hdr)

        # ─── Search bar ───
        sb = QFrame()
        sb.setStyleSheet(
            f"QFrame {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 10px; }}"
        )
        sl = QHBoxLayout(sb)
        sl.setContentsMargins(12, 0, 12, 0)
        sl.setSpacing(8)

        si = QLabel()
        si.setPixmap(I.search(FG_FAINT).pixmap(16, 16))
        sl.addWidget(si)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search applications...")
        self.search.setFont(QFont("Adwaita Sans", 13))
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {FG};
                border: none;
                padding: 8px 0;
                selection-background-color: {GREEN};
                selection-color: {BG};
            }}
            QLineEdit::placeholder {{
                color: {FG_FAINT};
            }}
        """)
        self.search.textChanged.connect(self._filter)
        sl.addWidget(self.search, 1)

        col.addWidget(sb)

        # ─── Tabs ───
        tabs = QHBoxLayout()
        tabs.setSpacing(6)

        self.tab_search = Pill("Search", I.search(FG_DIM))
        self.tab_search.set_active(True)
        self.tab_search.clicked.connect(lambda: self._set_mode("search"))

        self.tab_all = Pill("All Apps", I.grid(FG_DIM))
        self.tab_all.clicked.connect(lambda: self._set_mode("all"))

        tabs.addWidget(self.tab_search)
        tabs.addWidget(self.tab_all)
        tabs.addStretch()

        col.addLayout(tabs)

        # ─── Divider ───
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {BORDER};")
        col.addWidget(div)

        # ─── App list ───
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 5px;
                margin: 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {HOVER};
                border-radius: 2px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {FG_FAINT};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        self.list_w = QWidget()
        self.list_w.setStyleSheet("background: transparent;")
        self.list_lay = QVBoxLayout(self.list_w)
        self.list_lay.setContentsMargins(0, 4, 0, 0)
        self.list_lay.setSpacing(2)
        self.list_lay.addStretch()

        self.scroll.setWidget(self.list_w)
        col.addWidget(self.scroll, 1)

        # ─── Footer ───
        footer = QHBoxLayout()
        footer.setSpacing(12)

        hints = [
            ("Tab", "toggle"),
            ("↑↓", "navigate"),
            ("Enter", "launch"),
            ("Esc", "close"),
        ]
        for key, desc in hints:
            lbl = QLabel(f"{key} {desc}")
            lbl.setFont(QFont("Adwaita Sans", 8))
            lbl.setStyleSheet(f"color: {FG_FAINT}; background: transparent;")
            footer.addWidget(lbl)

        footer.addStretch()
        col.addLayout(footer)

        # ─── Shortcuts ───
        QShortcut(QKeySequence("Return"), self, self._launch)
        QShortcut(QKeySequence("Escape"), self, self.hide)
        QShortcut(QKeySequence("Down"), self, self._down)
        QShortcut(QKeySequence("Up"), self, self._up)
        QShortcut(QKeySequence("Tab"), self, self._toggle_mode)

    def _set_mode(self, mode):
        self.show_all = (mode == "all")
        self.tab_search.set_active(mode == "search")
        self.tab_all.set_active(mode == "all")
        self._filter()

    def _toggle_mode(self):
        self._set_mode("all" if self.show_all else "search")

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
            if not self.show_all:
                if not q or q not in app["name"].lower():
                    continue

            w = AppCard(app, idx, len(self.all_apps))
            w.mousePressEvent = lambda e, i=idx: self._sel(i)
            w.mouseDoubleClickEvent = lambda e, i=idx: (self._sel(i), self._launch())
            self.list_lay.insertWidget(self.list_lay.count() - 1, w)
            self.items.append(w)
            self.filtered.append(app)
            idx += 1

        self.count.setText(str(len(self.items)))
        if self.items:
            self._sel(0)

    def _sel(self, i):
        self.sel = min(max(i, 0), len(self.items) - 1)
        for j, w in enumerate(self.items):
            w.set_selected(j == self.sel)
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
            run_app(self.filtered[self.sel]["exec"])
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
