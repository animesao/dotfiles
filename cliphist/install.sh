#!/bin/bash
# cliphist installer

set -e

INSTALL_DIR="$HOME/.local/bin"
SERVICE_DIR="$HOME/.config/systemd/user"
CONFIG_DIR="$HOME/.config/cliphist"

echo "Installing cliphist..."

# Create dirs
mkdir -p "$INSTALL_DIR"
mkdir -p "$SERVICE_DIR"
mkdir -p "$CONFIG_DIR"

# Install TUI + daemon
cp "$(dirname "$0")/cliphist.py" "$INSTALL_DIR/cliphist"
chmod +x "$INSTALL_DIR/cliphist"
echo "Installed: $INSTALL_DIR/cliphist"

# Install GUI
cp "$(dirname "$0")/cliphist-gui.py" "$INSTALL_DIR/cliphist-gui"
chmod +x "$INSTALL_DIR/cliphist-gui"
echo "Installed: $INSTALL_DIR/cliphist-gui"

# Create default config
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

# Install systemd service
cp "$(dirname "$0")/cliphist.service" "$SERVICE_DIR/cliphist.service"
systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable --now cliphist.service 2>/dev/null || true
echo "Service enabled: cliphist.service"

# Add ~/.local/bin to PATH (for fish)
FISH_CONFIG="$HOME/.config/fish/conf.d"
mkdir -p "$FISH_CONFIG"
if [ ! -f "$FISH_CONFIG/path.fish" ]; then
    echo 'fish_add_path -g ~/.local/bin' > "$FISH_CONFIG/path.fish"
    echo "Added ~/.local/bin to fish PATH"
fi

# Add ~/.local/bin to PATH (for systemd/environment)
ENV_DIR="$HOME/.config/environment.d"
mkdir -p "$ENV_DIR"
if [ ! -f "$ENV_DIR/path.conf" ]; then
    echo 'PATH="${HOME}/.local/bin:${PATH}"' > "$ENV_DIR/path.conf"
    echo "Added ~/.local/bin to environment PATH"
fi

echo ""
echo "Done! Usage:"
echo "  cliphist          # Open TUI"
echo "  cliphist-gui      # Open GUI (Gruvbox)"
echo "  cliphist list     # List items"
echo "  cliphist count    # Show count"
echo "  cliphist clear    # Clear history"
echo ""
echo "Keybind (already in niri config):"
echo "  Mod+V → cliphist-gui"
echo ""
echo "Log out and back in for PATH changes to take effect."
