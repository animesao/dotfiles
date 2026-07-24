#!/usr/bin/env python3
"""
launcher — search-first app launcher for Wayland/niri
Design: Gruvbox dark, keyboard-first, zero decoration.
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

# ─── Gruvbox tokens ───
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

R      = 14
R_SM   = 8
ICON_S = 16


# ─── SVG icons (Feather-style, stroke-only) ───
def _svg_icon(svg, color, size=ICON_S):
    tag = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'{svg}</svg>'
    )
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    px.loadFromData(tag.encode())
    return QIcon(px)


class Icon:
    SEARCH = lambda c=FG_DIM: _svg_icon(
        '<circle cx="11" cy="11" r="7"/>'
        '<path d="M21 21l-4.35-4.35"/>', c)
    GRID = lambda c=FG_DIM: _svg_icon(
        '<rect x="3" y="3" width="7" height="7" rx="1"/>'
        '<rect x="14" y="3" width="7" height="7" rx="1"/>'
        '<rect x="3" y="14" width="7" height="7" rx="1"/>'
        '<rect x="14" y="14" width="7" height="7" rx="1"/>', c)
    BOLT = lambda c=FG_DIM: _svg_icon(
        '<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>', c)
    KEY = lambda c=FG_DIM: _svg_icon(
        '<path d="M21 2l-2 2m-7.6 7.6a2.5 2.5 0 1 1-3.5-3.5L14 4"/>'
        '<path d="M15.5 7.5L20 2"/>'
        '<path d="M18 14l-3.5 3.5a2 2 0 0 1-2.8 0L8 14"/>', c)
    TERMINAL = lambda c=FG_DIM: _svg_icon(
        '<polyline points="4 17 10 11 4 5"/>'
        '<line x1="12" y1="19" x2="20" y2="19"/>', c)


# ─── System icon loader ───
def _load_icon(name: str, size: int = 24) -> QPixmap:
    if not name:
        return QPixmap()
    icon = QIcon.fromTheme(name)
    if not icon.isNull():
        return icon.pixmap(size, size)
    for base in [
        Path.home() / ".local/share/icons/hicolor/scalable/apps",
        Path.home() / ".local/share/icons/hicolor/48x48/apps",
        Path("/usr/share/icons/hicolor/scalable/apps"),
        Path("/usr/share/icons/hicolor/48x48/apps"),
        Path("/usr/share/pixmaps"),
    ]:
        for ext in (".svg", ".png", ""):
            p = base / f"{name}{ext}"
            if p.exists():
                return QPixmap(str(p)).scaled(
                    size, size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
    return QPixmap()


# ─── Desktop file parser ───
_DESKTOP_DIRS = [
    Path.home() / ".local/share/applications",
    Path("/usr/share/applications"),
]


def _parse_desktop(f: Path) -> dict | None:
    try:
        text = f.read_text(errors="ignore")
    except Exception:
        return None
    name = exec_cmd = icon = ""
    no_display = False
    in_entry = False
    for line in text.splitlines():
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
        return {"name": name, "exec": exec_cmd, "icon": icon}
    return None


def _load_apps() -> list[dict]:
    apps = []
    seen = set()
    for d in _DESKTOP_DIRS:
        if not d.exists():
            continue
        for f in d.glob("*.desktop"):
            app = _parse_desktop(f)
            if app and app["name"] not in seen:
                apps.append(app)
                seen.add(app["name"])
    apps.sort(key=lambda a: a["name"].lower())
    return apps


# ─── Letter-circle fallback colors ───
_FALLBACK_COLORS = [GREEN, YELLOW, AQUA, BLUE, PURPLE, RED]


# ─── App row ───
class AppRow(QWidget):
    __slots__ = ("app", "_sel", "_hov")

    def __init__(self, app: dict, idx: int, show_idx: bool):
        super().__init__()
        self.app = app
        self._sel = False
        self._hov = False
        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(10)

        # icon
        ico = QLabel()
        ico.setFixedSize(24, 24)
        px = _load_icon(app.get("icon", ""), 24)
        if not px.isNull():
            ico.setPixmap(px)
        else:
            letter = app["name"][0].upper()
            c = _FALLBACK_COLORS[ord(letter) % len(_FALLBACK_COLORS)]
            ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ico.setFont(QFont("Adwaita Sans", 10, QFont.Weight.Bold))
            ico.setText(letter)
            ico.setStyleSheet(f"color:{BG}; background:{c}; border-radius:12px;")
        lay.addWidget(ico)

        # name + exec
        col = QVBoxLayout()
        col.setSpacing(0)
        col.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(app["name"])
        lbl.setFont(QFont("Adwaita Sans", 11, QFont.Weight.DemiBold))
        lbl.setStyleSheet(f"color:{FG}; background:transparent;")
        col.addWidget(lbl)

        exec_short = app["exec"].split()[0].split("/")[-1]
        sub = QLabel(exec_short)
        sub.setFont(QFont("Adwaita Sans", 8))
        sub.setStyleSheet(f"color:{FG_FAINT}; background:transparent;")
        col.addWidget(sub)

        lay.addLayout(col, 1)

        # idx badge (only when ≤10 items)
        if show_idx:
            badge = QLabel(str(idx + 1))
            badge.setFixedSize(20, 20)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFont(QFont("Adwaita Sans", 8, QFont.Weight.Bold))
            badge.setObjectName("badge")
            self._badge = badge
            self._update_badge()
            lay.addWidget(badge)

    def _update_badge(self):
        if not hasattr(self, "_badge"):
            return
        if self._sel:
            self._badge.setStyleSheet(
                f"color:{BG}; background:{GREEN}; border-radius:10px;")
        else:
            self._badge.setStyleSheet(
                f"color:{FG_FAINT}; background:{SURF_HI}; border-radius:10px;")

    def set_selected(self, s: bool):
        self._sel = s
        self._update_badge()
        self.update()

    def paintEvent(self, e):
        if not (self._sel or self._hov):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(GREEN if self._sel else HOVER))
        p.setOpacity(0.25 if self._sel else 0.35)
        p.drawRoundedRect(QRectF(self.rect()), R_SM, R_SM)
        p.end()

    def enterEvent(self, e):
        self._hov = True
        self.update()

    def leaveEvent(self, e):
        self._hov = False
        self.update()


# ─── Pill tab ───
class Pill(QPushButton):
    def __init__(self, text: str, icon_fn):
        super().__init__()
        self._on = False
        self.setText(f"  {text}")
        self.setIcon(icon_fn(FG_DIM))
        self.setIconSize(QSize(12, 12))
        self.setCheckable(True)
        self.setFixedHeight(26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Adwaita Sans", 9, QFont.Weight.Bold))
        self._paint()

    def _paint(self):
        if self._on:
            self.setStyleSheet(
                f"QPushButton{{background:{GREEN};color:{BG};border:none;"
                f"border-radius:13px;padding:0 14px;}}")
        else:
            self.setStyleSheet(
                f"QPushButton{{background:transparent;color:{FG_DIM};border:none;"
                f"border-radius:13px;padding:0 14px;}}"
                f"QPushButton:hover{{color:{FG};background:{HOVER};}}")

    def set_active(self, v: bool):
        self._on = v
        self.setChecked(v)
        self._paint()


# ─── Main launcher ───
class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self._apps: list[dict] = []
        self._filtered: list[dict] = []
        self._rows: list[AppRow] = []
        self._sel = 0
        self._show_all = False
        self._build()
        self._apps = _load_apps()

    def _build(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(500, 440)

        # shadow
        shadow = QFrame(self)
        shadow.setGeometry(4, 4, 492, 432)
        eff = QGraphicsDropShadowEffect()
        eff.setBlurRadius(50)
        eff.setOffset(0, 10)
        c = QColor(BG); c.setAlpha(180)
        eff.setColor(c)
        shadow.setGraphicsEffect(eff)

        # surface
        self.surf = QFrame(self)
        self.surf.setStyleSheet(
            f"QFrame{{background:{SURFACE};border:1px solid {BORDER};"
            f"border-radius:{R}px;}}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.surf)

        col = QVBoxLayout(self.surf)
        col.setContentsMargins(14, 12, 14, 12)
        col.setSpacing(10)

        # ── header ──
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background:{GREEN};border-radius:4px;")
        hdr.addWidget(dot)
        title = QLabel("Launcher")
        title.setFont(QFont("Adwaita Sans", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{FG};background:transparent;")
        hdr.addWidget(title)
        hdr.addStretch()
        self._count = QLabel("0")
        self._count.setFont(QFont("Adwaita Sans", 11))
        self._count.setStyleSheet(f"color:{FG_FAINT};background:transparent;")
        hdr.addWidget(self._count)
        col.addLayout(hdr)

        # ── search ──
        bar = QFrame()
        bar.setStyleSheet(
            f"QFrame{{background:{BG};border:1px solid {BORDER};border-radius:10px;}}")
        blay = QHBoxLayout(bar)
        blay.setContentsMargins(12, 0, 12, 0)
        blay.setSpacing(8)

        si = QLabel()
        si.setPixmap(Icon.SEARCH(FG_FAINT).pixmap(ICON_S, ICON_S))
        blay.addWidget(si)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Search applications...")
        self._input.setFont(QFont("Adwaita Sans", 13))
        self._input.setStyleSheet(
            f"QLineEdit{{background:transparent;color:{FG};border:none;padding:8px 0;"
            f"selection-background-color:{GREEN};selection-color:{BG};}}"
            f"QLineEdit::placeholder{{color:{FG_FAINT};}}")
        self._input.textChanged.connect(self._filter)
        blay.addWidget(self._input, 1)
        col.addWidget(bar)

        # ── tabs ──
        tabs = QHBoxLayout()
        tabs.setSpacing(6)
        self._tab_search = Pill("Search", Icon.SEARCH)
        self._tab_search.set_active(True)
        self._tab_search.clicked.connect(lambda: self._mode("search"))
        self._tab_all = Pill("All Apps", Icon.GRID)
        self._tab_all.clicked.connect(lambda: self._mode("all"))
        tabs.addWidget(self._tab_search)
        tabs.addWidget(self._tab_all)
        tabs.addStretch()
        col.addLayout(tabs)

        # ── divider ──
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{BORDER};")
        col.addWidget(div)

        # ── list ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            f"QScrollArea{{background:transparent;border:none;}}"
            f"QScrollBar:vertical{{background:transparent;width:5px;margin:4px 0;}}"
            f"QScrollBar::handle:vertical{{background:{HOVER};border-radius:2px;min-height:40px;}}"
            f"QScrollBar::handle:vertical:hover{{background:{FG_FAINT};}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}"
            f"QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:none;}}")

        self._list_w = QWidget()
        self._list_w.setStyleSheet("background:transparent;")
        self._list_lay = QVBoxLayout(self._list_w)
        self._list_lay.setContentsMargins(0, 4, 0, 0)
        self._list_lay.setSpacing(2)
        self._list_lay.addStretch()
        self._scroll.setWidget(self._list_w)
        col.addWidget(self._scroll, 1)

        # ── footer ──
        foot = QHBoxLayout()
        foot.setSpacing(16)
        for key, desc in [("Tab", "toggle"), ("↑↓", "nav"),
                          ("Enter", "open"), ("Esc", "close")]:
            l = QLabel(f"{key} {desc}")
            l.setFont(QFont("Adwaita Sans", 8))
            l.setStyleSheet(f"color:{FG_FAINT};background:transparent;")
            foot.addWidget(l)
        foot.addStretch()
        col.addLayout(foot)

        # ── shortcuts ──
        QShortcut(QKeySequence("Return"), self, self._launch)
        QShortcut(QKeySequence("Escape"), self, self.hide)
        QShortcut(QKeySequence("Down"), self, self._down)
        QShortcut(QKeySequence("Up"), self, self._up)
        QShortcut(QKeySequence("Tab"), self, self._toggle)

    # ── mode ──
    def _mode(self, m: str):
        self._show_all = m == "all"
        self._tab_search.set_active(m == "search")
        self._tab_all.set_active(m == "all")
        self._filter()

    def _toggle(self):
        self._mode("all" if self._show_all else "search")

    # ── filter ──
    def _filter(self):
        for w in self._rows:
            w.setParent(None)
            w.deleteLater()
        self._rows.clear()

        q = self._input.text().lower().strip()
        self._filtered = []
        idx = 0
        for app in self._apps:
            if not self._show_all:
                if not q or q not in app["name"].lower():
                    continue
            row = AppRow(app, idx, len(self._apps) <= 10)
            row.mousePressEvent = lambda e, i=idx: self._select(i)
            row.mouseDoubleClickEvent = lambda e, i=idx: (
                self._select(i), self._launch())
            self._list_lay.insertWidget(self._list_lay.count() - 1, row)
            self._rows.append(row)
            self._filtered.append(app)
            idx += 1

        self._count.setText(str(len(self._rows)))
        if self._rows:
            self._select(0)

    # ── selection ──
    def _select(self, i: int):
        self._sel = min(max(i, 0), len(self._rows) - 1)
        for j, r in enumerate(self._rows):
            r.set_selected(j == self._sel)
        if self._rows and 0 <= self._sel < len(self._rows):
            self._scroll.ensureWidgetVisible(self._rows[self._sel])

    def _down(self):
        if self._sel < len(self._rows) - 1:
            self._select(self._sel + 1)

    def _up(self):
        if self._sel > 0:
            self._select(self._sel - 1)

    # ── launch ──
    def _launch(self):
        if self._sel < len(self._filtered):
            try:
                subprocess.Popen(
                    self._filtered[self._sel]["exec"].split(),
                    start_new_session=True,
                )
            except Exception:
                pass
            self.hide()

    # ── show ──
    def open(self):
        self._input.clear()
        self._mode("search")
        self._filter()
        self._input.setFocus()
        s = QApplication.primaryScreen().geometry()
        self.move((s.width() - self.width()) // 2,
                  (s.height() - self.height()) // 2)
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

    w = Launcher()
    w.open()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
