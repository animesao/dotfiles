#!/bin/bash
# sddm config uninstaller

set -e

CONF="/etc/sddm.conf.d/dotfiles.conf"

echo "Removing SDDM config..."

if [ -f "$CONF" ]; then
    sudo rm "$CONF"
    echo "Removed: $CONF"
else
    echo "Config not found, skipping."
fi

sudo systemctl reload sddm 2>/dev/null || echo "SDDM reload skipped (may need reboot)"

echo "Done!"
