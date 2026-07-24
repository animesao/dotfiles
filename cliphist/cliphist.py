#!/usr/bin/env python3
"""
cliphist - Clipboard manager with history and search
Works with wl-clipboard (Wayland)
"""

import curses
import json
import os
import signal
import subprocess
import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

# Paths
DATA_DIR = Path.home() / ".local" / "share" / "cliphist"
HISTORY_FILE = DATA_DIR / "history.json"
IMAGES_DIR = DATA_DIR / "images"
PID_FILE = DATA_DIR / "daemon.pid"
CONFIG_FILE = Path.home() / ".config" / "cliphist" / "config.json"

# Defaults
MAX_ITEMS = 500
MAX_DISPLAY_LEN = 80


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_history(history: list):
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2))


def load_config() -> dict:
    defaults = {
        "max_items": MAX_ITEMS,
        "max_display_len": MAX_DISPLAY_LEN,
        "ignore_duplicates": True,
        "ignore_patterns": ["^\\s*$", "^\\s*$"],
    }
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text())
            defaults.update(cfg)
        except (json.JSONDecodeError, IOError):
            pass
    else:
        CONFIG_FILE.write_text(json.dumps(defaults, indent=2))
    return defaults


def get_clipboard_content() -> Optional[str]:
    try:
        result = subprocess.run(
            ["wl-paste", "-t", "text/plain"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_clipboard_image() -> Optional[str]:
    try:
        result = subprocess.run(
            ["wl-paste", "-t", "image/png"],
            capture_output=True, timeout=2
        )
        if result.returncode == 0 and len(result.stdout) > 100:
            h = hashlib.md5(result.stdout).hexdigest()[:12]
            img_path = IMAGES_DIR / f"{h}.png"
            if not img_path.exists():
                img_path.write_bytes(result.stdout)
            return f"[image:{img_path}]"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def matches_pattern(text: str, patterns: list) -> bool:
    import re
    for p in patterns:
        try:
            if re.search(p, text):
                return True
        except re.error:
            pass
    return False


def add_to_history(history: list, content: str, config: dict) -> list:
    if not content or not content.strip():
        return history

    if config.get("ignore_duplicates", True):
        history = [h for h in history if h.get("content") != content]

    item = {
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "pinned": False,
    }

    history.insert(0, item)

    max_items = config.get("max_items", MAX_ITEMS)
    if len(history) > max_items:
        history = [h for h in history if h.get("pinned", False)][:max_items]

    return history


# ─── Daemon Mode ───

def run_daemon():
    ensure_dirs()
    config = load_config()
    history = load_history()

    PID_FILE.write_text(str(os.getpid()))

    last_content = get_clipboard_content()

    def handle_exit(sig, frame):
        save_history(history)
        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    while True:
        time.sleep(0.5)

        # Re-read history in case GUI or other process modified it
        history = load_history()

        content = get_clipboard_content()
        if content and content != last_content:
            history = add_to_history(history, content, config)
            save_history(history)
            last_content = content

        image = get_clipboard_image()
        if image:
            history = add_to_history(history, image, config)
            save_history(history)


# ─── TUI Mode ───

class ClipHistTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.config = load_config()
        self.history = load_history()
        self.filtered = self.history[:]
        self.selected = 0
        self.search_query = ""
        self.search_mode = False
        self.scroll_offset = 0
        self.preview_mode = False
        self.status_msg = ""

        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()

        # Color pairs
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)    # header
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_YELLOW)  # selected
        curses.init_pair(3, curses.COLOR_CYAN, -1)                    # search
        curses.init_pair(4, curses.COLOR_GREEN, -1)                   # pinned
        curses.init_pair(5, curses.COLOR_RED, -1)                     # delete
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_GREEN)   # status
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLUE)    # help

    def get_max_display(self):
        return self.config.get("max_display_len", MAX_DISPLAY_LEN)

    def filter_items(self):
        if not self.search_query:
            self.filtered = self.history[:]
        else:
            q = self.search_query.lower()
            self.filtered = [
                h for h in self.history
                if q in h.get("content", "").lower()
            ]
        self.selected = min(self.selected, max(0, len(self.filtered) - 1))

    def draw(self):
        try:
            self.stdscr.clear()
            h, w = self.stdscr.getmaxyx()
            if h < 5 or w < 20:
                return

            # Header
            header = " cliphist "
            self.stdscr.attron(curses.color_pair(1))
            self.safe_addnstr(0, 0, header.ljust(w), w)
            self.stdscr.attroff(curses.color_pair(1))

            # Search bar
            if self.search_mode:
                search_text = f" Search: {self.search_query}_ "
                self.stdscr.attron(curses.color_pair(3))
                self.safe_addnstr(1, 0, search_text.ljust(w), w)
                self.stdscr.attroff(curses.color_pair(3))
            else:
                info = f" {len(self.filtered)} items "
                self.safe_addnstr(1, 0, info.ljust(w), w, curses.A_DIM)

            # List
            list_height = h - 3
            max_len = self.get_max_display()

            # Adjust scroll
            if self.selected < self.scroll_offset:
                self.scroll_offset = self.selected
            elif self.selected >= self.scroll_offset + list_height:
                self.scroll_offset = self.selected - list_height + 1

            for i in range(list_height):
                idx = i + self.scroll_offset
                if idx >= len(self.filtered):
                    break

                item = self.filtered[idx]
                content = item.get("content", "")

                # Truncate content
                if content.startswith("[image:"):
                    display = "[ image ]"
                else:
                    display = content.replace("\n", "↵")[:max_len]
                    if len(content) > max_len:
                        display += "…"

                # Line number
                line_num = f"{idx + 1:3d} "

                # Pin indicator
                pin = " ★ " if item.get("pinned", False) else "   "

                # Timestamp
                ts = ""
                if item.get("timestamp"):
                    try:
                        dt = datetime.fromisoformat(item["timestamp"])
                        ts = f" {dt.strftime('%H:%M')}"
                    except ValueError:
                        pass

                line = f"{line_num}{pin}{display}"

                y = i + 2
                attr = curses.A_NORMAL

                if idx == self.selected:
                    attr = curses.color_pair(2) | curses.A_BOLD
                    line = line[:w-1]
                elif item.get("pinned", False):
                    attr = curses.color_pair(4)

                self.safe_addnstr(y, 0, line.ljust(w), w, attr)

            # Status bar
            help_text = " q:quit  /:search  Enter:copy  p:pin  d:delete  ?:help "
            self.stdscr.attron(curses.color_pair(7))
            self.safe_addnstr(h-1, 0, help_text[:w-1].ljust(w), w)
            self.stdscr.attroff(curses.color_pair(7))

            self.stdscr.refresh()
        except curses.error:
            pass

    def safe_addnstr(self, y, x, text, n, attr=0):
        try:
            h, w = self.stdscr.getmaxyx()
            if 0 <= y < h and 0 <= x < w:
                self.stdscr.addnstr(y, x, text, min(n, w - x), attr)
        except curses.error:
            pass

    def copy_selected(self):
        if not self.filtered:
            return
        item = self.filtered[self.selected]
        content = item.get("content", "")

        if content.startswith("[image:"):
            img_path = content.replace("[image:", "").replace("]", "")
            if os.path.exists(img_path):
                try:
                    with open(img_path, "rb") as f:
                        img_data = f.read()
                    proc = subprocess.Popen(
                        ["wl-copy", "-t", "image/png"],
                        stdin=subprocess.PIPE
                    )
                    proc.communicate(input=img_data)
                    self.status_msg = "Image copied!"
                except Exception as e:
                    self.status_msg = f"Error: {e}"
        else:
            try:
                subprocess.run(
                    ["wl-copy"],
                    input=content.encode(),
                    check=True, timeout=2
                )
                self.status_msg = "Copied!"
            except Exception as e:
                self.status_msg = f"Error: {e}"

    def toggle_pin(self):
        if not self.filtered:
            return
        item = self.filtered[self.selected]
        item["pinned"] = not item.get("pinned", False)
        save_history(self.history)
        self.status_msg = "Pinned!" if item["pinned"] else "Unpinned"

    def delete_selected(self):
        if not self.filtered:
            return
        item = self.filtered[self.selected]
        if item in self.history:
            self.history.remove(item)
        save_history(self.history)
        self.filter_items()
        self.status_msg = "Deleted"

    def show_help(self):
        try:
            h, w = self.stdscr.getmaxyx()
            help_lines = [
                " cliphist - Help ",
                "",
                " Navigation:",
                "   ↑/↓ or j/k    Move up/down",
                "   PgUp/PgDn     Page up/down",
                "   Home/End      First/last item",
                "",
                " Actions:",
                "   Enter          Copy to clipboard",
                "   /              Search mode",
                "   Esc            Cancel search",
                "   p              Pin/unpin item",
                "   d              Delete item",
                "   r              Refresh history",
                "   q              Quit",
                "",
                " Press any key to close...",
            ]

            box_h = len(help_lines) + 2
            box_w = min(max(len(l) for l in help_lines) + 4, w - 2)
            start_y = max(0, (h - box_h) // 2)
            start_x = max(0, (w - box_w) // 2)

            # Draw box
            self.stdscr.attron(curses.color_pair(7))
            for i in range(min(box_h, h)):
                self.safe_addnstr(start_y + i, start_x, " " * box_w, box_w)
            self.stdscr.attroff(curses.color_pair(7))

            for i, line in enumerate(help_lines):
                if start_y + i + 1 >= h:
                    break
                self.safe_addnstr(
                    start_y + i + 1, start_x + 2,
                    line[:box_w - 4], box_w - 4,
                    curses.color_pair(7) if i == 0 else curses.A_NORMAL
                )

            self.stdscr.refresh()
            self.stdscr.getch()
        except curses.error:
            pass

    def run(self):
        while True:
            self.draw()

            if self.status_msg:
                try:
                    h, w = self.stdscr.getmaxyx()
                    self.stdscr.attron(curses.color_pair(6))
                    self.safe_addnstr(h-2, 0, f" {self.status_msg} ".ljust(w), w)
                    self.stdscr.attroff(curses.color_pair(6))
                    self.stdscr.refresh()
                    self.stdscr.timeout(1500)
                    self.stdscr.getch()
                    self.stdscr.timeout(-1)
                except curses.error:
                    pass
                self.status_msg = ""

            key = self.stdscr.getch()

            if self.search_mode:
                if key == 27:  # Esc
                    self.search_mode = False
                    self.search_query = ""
                    self.filter_items()
                elif key == 10:  # Enter
                    self.search_mode = False
                elif key == 127 or key == curses.KEY_BACKSPACE:
                    self.search_query = self.search_query[:-1]
                    self.filter_items()
                elif 32 <= key <= 126:
                    self.search_query += chr(key)
                    self.filter_items()
                continue

            if key == ord('q'):
                break
            elif key == ord('/') or key == ord('f'):
                self.search_mode = True
                self.search_query = ""
            elif key == ord('j') or key == curses.KEY_DOWN:
                self.selected = min(self.selected + 1, len(self.filtered) - 1)
            elif key == ord('k') or key == curses.KEY_UP:
                self.selected = max(self.selected - 1, 0)
            elif key == curses.KEY_NPAGE:  # Page Down
                self.selected = min(self.selected + 10, len(self.filtered) - 1)
            elif key == curses.KEY_PPAGE:  # Page Up
                self.selected = max(self.selected - 10, 0)
            elif key == curses.KEY_HOME:
                self.selected = 0
            elif key == curses.KEY_END:
                self.selected = max(0, len(self.filtered) - 1)
            elif key == 10:  # Enter
                self.copy_selected()
            elif key == ord('p'):
                self.toggle_pin()
            elif key == ord('d'):
                self.delete_selected()
            elif key == ord('r'):
                self.history = load_history()
                self.filter_items()
                self.status_msg = "Refreshed"
            elif key == ord('?') or key == ord('h'):
                self.show_help()


def main():
    ensure_dirs()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "daemon":
            run_daemon()
        elif cmd == "clear":
            save_history([])
            print("History cleared")
        elif cmd == "list":
            history = load_history()
            for i, item in enumerate(history[:20]):
                content = item.get("content", "")[:60].replace("\n", " ")
                print(f"{i+1:3d}. {content}")
        elif cmd == "count":
            history = load_history()
            print(f"{len(history)} items")
        elif cmd == "copy":
            if len(sys.argv) > 2:
                idx = int(sys.argv[2]) - 1
                history = load_history()
                if 0 <= idx < len(history):
                    content = history[idx].get("content", "")
                    subprocess.run(["wl-copy"], input=content.encode())
                    print(f"Copied item {idx+1}")
        elif cmd == "status":
            if PID_FILE.exists():
                pid = PID_FILE.read_text().strip()
                try:
                    os.kill(int(pid), 0)
                    print(f"Daemon running (PID: {pid})")
                except (ProcessLookupError, ValueError):
                    print("Daemon not running (stale PID)")
            else:
                print("Daemon not running")
        else:
            print(f"Usage: {sys.argv[0]} [daemon|list|clear|count|copy N|status]")
    else:
        # TUI mode
        curses.wrapper(lambda stdscr: ClipHistTUI(stdscr).run())


if __name__ == "__main__":
    main()
