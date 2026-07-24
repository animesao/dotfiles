#!/bin/bash
# Screenshot: focused window
DIR="$HOME/Pictures/screenshots"
mkdir -p "$DIR"
FILE="$DIR/screenshot_$(date +%Y%m%d_%H%M%S).png"
GEO=$(niri msg -j focused-window 2>/dev/null | jq -r '"\(.layout.tile_size[0])x\(.layout.tile_size[1])"' 2>/dev/null)
if [ -n "$GEO" ] && [ "$GEO" != "nullxnull" ]; then
    grim -g "$GEO" "$FILE" && wl-copy -t image/png < "$FILE" && notify-send -t 2000 "Screenshot" "Saved: $(basename "$FILE")"
else
    notify-send -t 2000 "Screenshot" "No focused window found"
fi
