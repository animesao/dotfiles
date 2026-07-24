#!/bin/bash
# sddm config + theme installer

set -e

SCRIPT_DIR="$(dirname "$0")"
CONF_DIR="/etc/sddm.conf.d"
THEME_DIR="/usr/share/sddm/themes/silent"

echo "Installing SDDM config + theme..."

# Create conf.d dir if it doesn't exist
sudo mkdir -p "$CONF_DIR"

# Remove old single-file config if it exists
if [ -f /etc/sddm.conf ]; then
    echo "Removing /etc/sddm.conf (moving to conf.d)..."
    sudo rm /etc/sddm.conf
fi

# Install config
sudo cp "$SCRIPT_DIR/sddm.conf" "$CONF_DIR/dotfiles.conf"
echo "Installed: $CONF_DIR/dotfiles.conf"

# Install theme
if [ -d "$SCRIPT_DIR/silent-theme" ]; then
    echo "Installing silent theme..."
    sudo rm -rf "$THEME_DIR"
    sudo cp -r "$SCRIPT_DIR/silent-theme" "$THEME_DIR"
    echo "Installed: $THEME_DIR"
fi

# Reload SDDM
echo "Reloading SDDM..."
sudo systemctl reload sddm 2>/dev/null || echo "SDDM reload skipped (may need reboot)"

echo ""
echo "Done! SDDM config + theme installed."
echo "Note: changes take effect on next login or reboot."
