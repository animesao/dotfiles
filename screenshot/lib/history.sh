#!/bin/bash
# Screenshot history management

HISTORY_FILE="${SAVE_DIR:-$HOME/Pictures/screenshots}/.history"

# Add screenshot to history
history_add() {
    local filepath="$1"
    local timestamp
    timestamp=$(date -Iseconds)

    if [ "$HISTORY_ENABLED" != "true" ]; then
        return
    fi

    mkdir -p "$(dirname "$HISTORY_FILE")"
    echo "${timestamp}|${filepath}" >> "$HISTORY_FILE"

    # Trim history
    if [ -f "$HISTORY_FILE" ]; then
        local count
        count=$(wc -l < "$HISTORY_FILE")
        if [ "$count" -gt "${HISTORY_MAX:-100}" ]; then
            tail -n "${HISTORY_MAX:-100}" "$HISTORY_FILE" > "${HISTORY_FILE}.tmp"
            mv "${HISTORY_FILE}.tmp" "$HISTORY_FILE"
        fi
    fi
}

# List recent screenshots
history_list() {
    local count="${1:-10}"

    if [ ! -f "$HISTORY_FILE" ]; then
        print_info "No history yet"
        return
    fi

    tail -n "$count" "$HISTORY_FILE" | while IFS='|' read -r ts filepath; do
        if [ -f "$filepath" ]; then
            local name
            name=$(basename "$filepath")
            local size
            size=$(du -h "$filepath" | cut -f1)
            echo -e "  \033[36m${ts}\033[0m  ${name}  (${size})"
        fi
    done
}

# Open last screenshot
history_last() {
    if [ ! -f "$HISTORY_FILE" ]; then
        print_err "No history"
        return 1
    fi

    local last
    last=$(tail -1 "$HISTORY_FILE" | cut -d'|' -f2)

    if [ -f "$last" ]; then
        echo "$last"
    else
        print_err "File not found: $last"
        return 1
    fi
}

# Browse history (simple fzf/catppuccin style)
history_browse() {
    if [ ! -f "$HISTORY_FILE" ]; then
        print_info "No history yet"
        return
    fi

    if ! command -v fzf &>/dev/null; then
        history_list 20
        return
    fi

    local selected
    selected=$(tail -20 "$HISTORY_FILE" | \
        awk -F'|' '{print $2}' | \
        while read -r f; do [ -f "$f" ] && basename "$f"; done | \
        fzf --prompt="Screenshot > " --height=40% --reverse)

    if [ -n "$selected" ]; then
        local filepath
        filepath=$(grep "$selected" "$HISTORY_FILE" | tail -1 | cut -d'|' -f2)
        echo "$filepath"
    fi
}
