#!/bin/bash
# sddm config + theme uninstaller

set -e

CONF="/etc/sddm.conf.d/dotfiles.conf"

echo "Removing SDDM config..."

if [ -f "$CONF" ]; then
    sudo rm "$CONF"
    echo "Removed: $CONF"
else
    echo "Config not found, skipping."
fi

echo "Removing silent theme..."
sudo rm -rf /usr/share/sddm/themes/silent
echo "Removed: /usr/share/sddm/themes/silent"

sudo systemctl reload sddm 2>/dev/null || echo "SDDM reload skipped (may need reboot)"

echo "Done!"
