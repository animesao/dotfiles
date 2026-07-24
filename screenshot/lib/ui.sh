#!/bin/bash
# UI helpers: notifications, clipboard, file operations

# Save image data to file
save_image() {
    local data="$1"
    local filepath="$2"

    mkdir -p "$(dirname "$filepath")"
    echo "$data" > "$filepath"
}

# Copy image to clipboard
copy_clipboard() {
    local filepath="$1"
    wl-copy -t image/png < "$filepath"
}

# Send notification
send_notify() {
    local filepath="$1"
    local filename
    filename=$(basename "$filepath")

    if [ "$NOTIFY" = "true" ] && command -v notify-send &>/dev/null; then
        notify-send \
            -t "$NOTIFY_TIMEOUT" \
            -a "screenshot" \
            -i "$filepath" \
            "Screenshot saved" \
            "$filename"
    fi
}

# Generate filepath from config
make_filepath() {
    local format="${FILENAME_FORMAT:-screenshot_%Y%m%d_%H%M%S.png}"
    local filename
    filename=$(date +"$format")
    echo "${SAVE_DIR:-$HOME/Pictures/screenshots}/$filename"
}

# Open in editor
open_editor() {
    local filepath="$1"

    if [ -z "$EDITOR" ] || [ "$EDITOR" = "none" ]; then
        return 1
    fi

    if ! command -v "$EDITOR" &>/dev/null; then
        send_notify "$filepath"
        return 1
    fi

    case "$EDITOR" in
        satty)
            $EDITOR $EDITOR_ARGS "$filepath" &
            ;;
        swappy)
            wl-copy -t image/png < "$filepath"
            $EDITOR &
            ;;
        gimp)
            $EDITOR "$filepath" &
            ;;
        *)
            $EDITOR "$filepath" &
            ;;
    esac
}

# Print colored output
print_ok() { echo -e "\033[32m[+]\033[0m $1"; }
print_err() { echo -e "\033[31m[-]\033[0m $1"; }
print_info() { echo -e "\033[36m[i]\033[0m $1"; }
