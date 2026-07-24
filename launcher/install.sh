#!/bin/bash
# launcher installer

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/bin"

echo "Installing launcher..."

mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/launcher.py" "$INSTALL_DIR/launcher"
chmod +x "$INSTALL_DIR/launcher"
echo "Installed: $INSTALL_DIR/launcher"

echo ""
echo "Done! Usage:"
echo "  launcher           # Open launcher"
echo ""
echo "Keybind:"
echo "  Ctrl+Mod+Return → launcher"
