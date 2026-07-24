#!/bin/bash
# cliphist installer

set -e

INSTALL_DIR="$HOME/.local/bin"
SERVICE_DIR="$HOME/.config/systemd/user"

echo "Installing cliphist..."

# Create dirs
mkdir -p "$INSTALL_DIR"
mkdir -p "$SERVICE_DIR"

# Install script
cp cliphist.py "$INSTALL_DIR/cliphist"
chmod +x "$INSTALL_DIR/cliphist"
echo "Installed: $INSTALL_DIR/cliphist"

# Install service
cp cliphist.service "$SERVICE_DIR/cliphist.service"
systemctl --user daemon-reload
systemctl --user enable --now cliphist.service
echo "Service enabled: cliphist.service"

# Create default config
CONFIG_DIR="$HOME/.config/cliphist"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cat > "$CONFIG_DIR/config.json" << 'EOF'
{
  "max_items": 500,
  "max_display_len": 80,
  "ignore_duplicates": true
}
EOF
    echo "Config created: $CONFIG_DIR/config.json"
fi

echo ""
echo "Done! Usage:"
echo "  cliphist          # Open TUI"
echo "  cliphist list     # List items"
echo "  cliphist count    # Show count"
echo "  cliphist clear    # Clear history"
echo "  cliphist status   # Check daemon"
echo ""
echo "Add to niri keybinds:"
echo '  Mod+V { spawn "cliphist"; }'
