#!/bin/bash
# Dotfiles Installer
# Usage: ./install.sh

set -e

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$HOME/.dotfiles-backup/$(date +%Y%m%d_%H%M%S)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

backup() {
    local src="$1"
    if [ -e "$src" ]; then
        mkdir -p "$BACKUP_DIR"
        cp -r "$src" "$BACKUP_DIR/"
        info "Backed up: $src"
    fi
}

link() {
    local src="$1"
    local dest="$2"
    
    backup "$dest"
    
    if [ -L "$dest" ]; then
        rm "$dest"
    elif [ -e "$dest" ]; then
        rm -rf "$dest"
    fi
    
    mkdir -p "$(dirname "$dest")"
    ln -sf "$src" "$dest"
    info "Linked: $dest -> $src"
}

# Install packages (Arch/CachyOS)
install_packages() {
    info "Installing required packages..."
    
    sudo pacman -S --needed --noconfirm \
        niri \
        alacritty \
        fish \
        htop \
        micro \
        btop \
        waybar \
        cliphist \
        wl-clipboard \
        grim \
        slurp \
        swaybg \
        polkit-gnome \
        pipewire \
        wireplumber \
        pavucontrol \
        brightnessctl \
        network-manager-applet \
       托盘图标 \
        2>/dev/null || true
    
    # AUR packages
    if command -v yay &> /dev/null; then
        yay -S --needed --noconfirm \
            noctalia-shell-bin 2>/dev/null || true
    fi
}

# Setup configs
setup_configs() {
    info "Setting up configurations..."
    
    # niri
    link "$DOTFILES_DIR/niri" "$HOME/.config/niri"
    
    # noctalia
    link "$DOTFILES_DIR/noctalia" "$HOME/.config/noctalia"
    
    # alacritty
    link "$DOTFILES_DIR/alacritty" "$HOME/.config/alacritty"
    
    # fish
    link "$DOTFILES_DIR/fish" "$HOME/.config/fish"
    
    # htop
    link "$DOTFILES_DIR/htop" "$HOME/.config/htop"
    
    # micro
    link "$DOTFILES_DIR/micro" "$HOME/.config/micro"
    
    # gtk
    link "$DOTFILES_DIR/gtk-3.0" "$HOME/.config/gtk-3.0"
}

# Set fish as default shell
setup_shell() {
    if [ "$SHELL" != "/usr/bin/fish" ]; then
        info "Setting fish as default shell..."
        chsh -s /usr/bin/fish
    fi
}

# Main
main() {
    echo ""
    echo "=================================="
    echo "   Dotfiles Installer"
    echo "=================================="
    echo ""
    
    # Check if running from dotfiles directory
    if [ ! -f "$DOTFILES_DIR/install.sh" ]; then
        error "Please run this script from the dotfiles directory"
        exit 1
    fi
    
    # Install packages
    read -p "Install required packages? (y/N): " install_pkgs
    if [[ "$install_pkgs" =~ ^[Yy]$ ]]; then
        install_packages
    fi
    
    # Setup configs
    setup_configs
    
    # Setup shell
    read -p "Set fish as default shell? (y/N): " setup_fish
    if [[ "$setup_fish" =~ ^[Yy]$ ]]; then
        setup_shell
    fi
    
    echo ""
    info "Installation complete!"
    info "Backup saved to: $BACKUP_DIR"
    echo ""
    info "Log out and log back in for changes to take effect."
    echo ""
}

main "$@"
