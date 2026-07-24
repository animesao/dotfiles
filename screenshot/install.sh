#!/bin/bash
# screenshot utility installer

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/screenshot"

echo "Installing screenshot utility..."

# Install main script
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/screenshot" "$INSTALL_DIR/screenshot"
chmod +x "$INSTALL_DIR/screenshot"
echo "Installed: $INSTALL_DIR/screenshot"

# Install libraries
mkdir -p "$INSTALL_DIR/screenshot-lib"
cp "$SCRIPT_DIR"/lib/*.sh "$INSTALL_DIR/screenshot-lib/"
chmod +x "$INSTALL_DIR/screenshot-lib/"*.sh
echo "Installed: $INSTALL_DIR/screenshot-lib/"

# Fix library path in main script
sed -i "s|SCRIPT_DIR=.*|SCRIPT_DIR=\"$INSTALL_DIR/screenshot-lib\"|" "$INSTALL_DIR/screenshot"

# Create config if not exists
if [ ! -f "$CONFIG_DIR/config" ]; then
    mkdir -p "$CONFIG_DIR"
    cp "$SCRIPT_DIR/screenshot.conf" "$CONFIG_DIR/config"
    echo "Config created: $CONFIG_DIR/config"
else
    echo "Config exists: $CONFIG_DIR/config"
fi

# Create screenshot directory
mkdir -p "$HOME/Pictures/screenshots"
echo "Screenshot dir: $HOME/Pictures/screenshots"

# Check dependencies
echo ""
echo "Checking dependencies..."
for cmd in grim slurp wl-copy notify-send jq; do
    if command -v "$cmd" &>/dev/null; then
        echo "  [ok] $cmd"
    else
        echo "  [!!] $cmd not found"
    fi
done

echo ""
echo "Done! Usage:"
echo "  screenshot           # Region capture"
echo "  screenshot window    # Focused window"
echo "  screenshot screen    # All outputs"
echo "  screenshot edit      # Region + editor"
echo "  screenshot history   # Browse history"
echo ""
echo "Keybinds (already in niri config):"
echo "  Ctrl+Shift+1  → region"
echo "  Ctrl+Shift+2  → screen"
echo "  Ctrl+Shift+3  → window"
echo "  Mod+Shift+S   → edit"
