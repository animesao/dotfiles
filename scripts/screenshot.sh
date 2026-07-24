#!/bin/bash
# screenshot — Wayland screenshot utility for niri
# Usage: screenshot.sh [command]
#
# Commands:
#   region    Select area (default)
#   window    Capture focused window
#   screen    Capture all outputs
#   output    Capture focused output
#   edit      Select area and open in editor
#   timer N   Screenshot after N seconds
#
# Keybinds (niri):
#   Ctrl+Shift+1  → region
#   Ctrl+Shift+2  → screen
#   Ctrl+Shift+3  → window
#   Mod+Shift+S   → edit

set -euo pipefail

# ─── Config ───
SAVE_DIR="${SCREENSHOT_DIR:-$HOME/Pictures/screenshots}"
EDITOR="${SCREENSHOT_EDITOR:-satty}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="screenshot_${TIMESTAMP}.png"
FILEPATH="$SAVE_DIR/$FILENAME"

# ─── Helpers ───
notify() {
    local img="$1"
    if command -v notify-send &>/dev/null; then
        notify-send -t 3000 -i "$img" "Screenshot saved" "$FILEPATH"
    fi
}

copy_clip() {
    local img="$1"
    if command -v wl-copy &>/dev/null; then
        wl-copy -t image/png < "$img"
    fi
}

save() {
    local data="$1"
    mkdir -p "$SAVE_DIR"
    echo "$data" > "$FILEPATH"
}

# ─── Get focused window geometry from niri ───
get_focused_window() {
    if command -v niri &>/dev/null; then
        niri msg -j focused-window 2>/dev/null | jq -r '.logical rect | "\(.x),\(.y) \(.width)x\(.height)"' 2>/dev/null
    fi
}

# ─── Commands ───
cmd_region() {
    local geo
    geo=$(slurp) || return 1
    grim -g "$geo" - | save "$(cat)"
    copy_clip "$FILEPATH"
    notify "$FILEPATH"
}

cmd_window() {
    local geo
    geo=$(get_focused_window)
    if [ -n "$geo" ]; then
        grim -g "$geo" - | save "$(cat)"
    else
        geo=$(slurp -w) || return 1
        grim -g "$geo" - | save "$(cat)"
    fi
    copy_clip "$FILEPATH"
    notify "$FILEPATH"
}

cmd_screen() {
    grim - | save "$(cat)"
    copy_clip "$FILEPATH"
    notify "$FILEPATH"
}

cmd_output() {
    local output
    output=$(niri msg -j focused-output 2>/dev/null | jq -r '.name' 2>/dev/null)
    if [ -n "$output" ]; then
        grim -o "$output" - | save "$(cat)"
        copy_clip "$FILEPATH"
        notify "$FILEPATH"
    else
        cmd_screen
    fi
}

cmd_edit() {
    local geo
    geo=$(slurp) || return 1
    grim -g "$geo" - | save "$(cat)"
    copy_clip "$FILEPATH"

    if command -v "$EDITOR" &>/dev/null; then
        "$EDITOR" "$FILEPATH" &
    else
        notify "$FILEPATH"
    fi
}

cmd_timer() {
    local delay="${1:-3}"
    notify-send -t $((delay * 1000)) "Screenshot" "Taking screenshot in ${delay}s..."
    sleep "$delay"
    grim - | save "$(cat)"
    copy_clip "$FILEPATH"
    notify "$FILEPATH"
}

# ─── Main ───
case "${1:-region}" in
    region)  cmd_region  ;;
    window)  cmd_window  ;;
    screen)  cmd_screen  ;;
    output)  cmd_output  ;;
    edit)    cmd_edit    ;;
    timer)   cmd_timer "$2" ;;
    *)
        echo "Usage: $(basename "$0") [region|window|screen|output|edit|timer N]"
        exit 1
        ;;
esac
