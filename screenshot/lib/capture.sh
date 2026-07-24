#!/bin/bash
# Core capture functions

# Capture region
capture_region() {
    local geo
    geo=$(slurp -d) || return 1
    grim -g "$geo" -f png -
}

# Capture focused window via niri
capture_window() {
    local geo
    geo=$(niri msg -j focused-window 2>/dev/null | \
        jq -r '"\(.layout.tile_size[0])x\(.layout.tile_size[1])"' 2>/dev/null)

    if [ -z "$geo" ] || [ "$geo" = "nullxnull" ]; then
        # Fallback: let user select window
        geo=$(slurp -w) || return 1
    fi

    grim -g "$geo" -f png -
}

# Capture all outputs
capture_screen() {
    grim -f png -
}

# Capture focused output
capture_output() {
    local output
    output=$(niri msg -j focused-output 2>/dev/null | jq -r '.name' 2>/dev/null)

    if [ -n "$output" ] && [ "$output" != "null" ]; then
        grim -o "$output" -f png -
    else
        grim -f png -
    fi
}

# Capture with delay
capture_delay() {
    local seconds="${1:-$TIMER_DEFAULT}"
    local i=$seconds

    while [ $i -gt 0 ]; do
        notify-send -t 1000 -a "screenshot" "Screenshot" "Taking screenshot in ${i}s..."
        sleep 1
        i=$((i - 1))
    done

    grim -f png -
}
