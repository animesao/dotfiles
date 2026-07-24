#!/bin/bash
# Screenshot: full screen
DIR="$HOME/Pictures/screenshots"
mkdir -p "$DIR"
FILE="$DIR/screenshot_$(date +%Y%m%d_%H%M%S).png"
grim "$FILE" && wl-copy -t image/png < "$FILE" && notify-send -t 2000 "Screenshot" "Saved: $(basename "$FILE")"
