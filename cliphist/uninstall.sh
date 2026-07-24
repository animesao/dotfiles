#!/bin/bash
# cliphist uninstaller

echo "Removing cliphist..."

# Stop service
systemctl --user stop cliphist.service 2>/dev/null || true
systemctl --user disable cliphist.service 2>/dev/null || true

# Remove files
rm -f "$HOME/.local/bin/cliphist"
rm -f "$HOME/.local/bin/cliphist-gui"
rm -f "$HOME/.config/systemd/user/cliphist.service"
rm -rf "$HOME/.config/cliphist"

# Remove PATH entries
rm -f "$HOME/.config/fish/conf.d/path.fish"
rm -f "$HOME/.config/environment.d/path.conf"

# Reload
systemctl --user daemon-reload 2>/dev/null || true

echo "Done. History preserved at ~/.local/share/cliphist/"
echo "Remove history: rm -rf ~/.local/share/cliphist"
