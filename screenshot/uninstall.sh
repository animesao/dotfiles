#!/bin/bash
# screenshot utility uninstaller

set -e

echo "Removing screenshot utility..."

rm -f "$HOME/.local/bin/screenshot"
rm -rf "$HOME/.local/bin/screenshot-lib"

echo "Removed: ~/.local/bin/screenshot"
echo "Removed: ~/.local/bin/screenshot-lib/"
echo ""
echo "Config preserved at: ~/.config/screenshot/"
echo "Screenshots preserved at: ~/Pictures/screenshots/"
echo ""
echo "To remove config: rm -rf ~/.config/screenshot"
echo "To remove screenshots: rm -rf ~/Pictures/screenshots"
