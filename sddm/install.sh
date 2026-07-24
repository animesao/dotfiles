#!/bin/bash
# sddm config installer

set -e

CONF_DIR="/etc/sddm.conf.d"

echo "Installing SDDM config..."

# Create conf.d dir if it doesn't exist
sudo mkdir -p "$CONF_DIR"

# Remove old single-file config if it exists
if [ -f /etc/sddm.conf ]; then
    echo "Removing /etc/sddm.conf (moving to conf.d)..."
    sudo rm /etc/sddm.conf
fi

# Install config
sudo cp "$(dirname "$0")/sddm.conf" "$CONF_DIR/dotfiles.conf"
echo "Installed: $CONF_DIR/dotfiles.conf"

# Reload SDDM
echo "Reloading SDDM..."
sudo systemctl reload sddm 2>/dev/null || echo "SDDM reload skipped (may need reboot)"

echo ""
echo "Done! SDDM config installed."
echo "Note: changes take effect on next login or reboot."
