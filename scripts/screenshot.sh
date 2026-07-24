#!/bin/bash
# Screenshot utility for Wayland (grim + slurp)
# Usage: screenshot.sh [full|region|window]

DIR="$HOME/Pictures/screenshots"
mkdir -p "$DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

case "${1:-region}" in
    full)
        grim "$DIR/screenshot_$TIMESTAMP.png"
        ;;
    region)
        grim -g "$(slurp)" "$DIR/screenshot_$TIMESTAMP.png"
        ;;
    window)
        grim -g "$(slurp -w)" "$DIR/screenshot_$TIMESTAMP.png"
        ;;
    *)
        echo "Usage: $0 [full|region|window]"
        exit 1
        ;;
esac

if [ -f "$DIR/screenshot_$TIMESTAMP.png" ]; then
    wl-copy -t image/png < "$DIR/screenshot_$TIMESTAMP.png"
    notify-send "Screenshot saved" "$DIR/screenshot_$TIMESTAMP.png"
fi
