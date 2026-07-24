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
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }
checking() { echo -ne "${CYAN}[?]${NC} Checking $1... "; }

# Check if command exists
check_cmd() {
    command -v "$1" &> /dev/null
}

# Install package if missing
install_if_missing() {
    local pkg="$1"
    local cmd="${2:-$1}"
    
    checking "$pkg"
    if check_cmd "$cmd"; then
        echo -e "${GREEN}installed${NC}"
    else
        echo -e "${YELLOW}not found, installing...${NC}"
        sudo pacman -S --needed --noconfirm "$pkg" 2>/dev/null && \
            info "$pkg installed" || \
            warn "Failed to install $pkg (may need AUR)"
    fi
}

# Install AUR package if missing
install_aur_if_missing() {
    local pkg="$1"
    local cmd="${2:-$1}"
    
    if ! check_cmd "yay"; then
        warn "yay not found, skipping AUR package: $pkg"
        return
    fi
    
    checking "$pkg"
    if check_cmd "$cmd"; then
        echo -e "${GREEN}installed${NC}"
    else
        echo -e "${YELLOW}not found, installing from AUR...${NC}"
        yay -S --needed --noconfirm "$pkg" 2>/dev/null && \
            info "$pkg installed" || \
            warn "Failed to install $pkg"
    fi
}

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

# Check and install all required programs
check_and_install() {
    echo ""
    echo -e "${CYAN}━━━ System Packages ━━━${NC}"
    
    # Core
    install_if_missing "niri"
    install_if_missing "alacritty"
    install_if_missing "fish"
    install_if_missing "htop"
    install_if_missing "micro"
    install_if_missing "btop"
    install_if_missing "git"
    install_if_missing "curl"
    install_if_missing "wget"
    install_if_missing "unzip"
    
    # Wayland utils
    install_if_missing "wl-clipboard"
    install_if_missing "cliphist"
    install_if_missing "grim"
    install_if_missing "slurp"
    install_if_missing "swaybg"
    install_if_missing "polkit-gnome"
    install_if_missing "brightnessctl"
    install_if_missing "nm-applet"
    
    # Audio
    install_if_missing "pipewire"
    install_if_missing "wireplumber"
    install_if_missing "pavucontrol"
    
    # Fonts
    install_if_missing "noto-fonts"
    install_if_missing "noto-fonts-cjk"
    install_if_missing "noto-fonts-emoji"
    install_if_missing "ttf-font-awesome"
    
    echo ""
    echo -e "${CYAN}━━━ AUR Packages ━━━${NC}"
    
    install_aur_if_missing "noctalia-shell-bin" "noctalia-shell"
    
    echo ""
}

# Setup configs
setup_configs() {
    echo -e "${CYAN}━━━ Setting up configs ━━━${NC}"

    # Window manager & desktop
    link "$DOTFILES_DIR/niri" "$HOME/.config/niri"
    link "$DOTFILES_DIR/noctalia" "$HOME/.config/noctalia"
    link "$DOTFILES_DIR/autostart" "$HOME/.config/autostart"

    # Terminal & shell
    link "$DOTFILES_DIR/alacritty" "$HOME/.config/alacritty"
    link "$DOTFILES_DIR/fish" "$HOME/.config/fish"

    # Editors
    link "$DOTFILES_DIR/micro" "$HOME/.config/micro"
    link "$DOTFILES_DIR/vscodium" "$HOME/.config/VSCodium/User"

    # System utils
    link "$DOTFILES_DIR/htop" "$HOME/.config/htop"

    # GTK theming
    link "$DOTFILES_DIR/gtk-3.0" "$HOME/.config/gtk-3.0"
    link "$DOTFILES_DIR/gtk-4.0" "$HOME/.config/gtk-4.0"

    # Apps
    link "$DOTFILES_DIR/qbittorrent" "$HOME/.config/qBittorrent"

    # XDG
    link "$DOTFILES_DIR/user-dirs.dirs" "$HOME/.config/user-dirs.dirs"
    link "$DOTFILES_DIR/user-dirs.locale" "$HOME/.config/user-dirs.locale"
    link "$DOTFILES_DIR/mimeapps.list" "$HOME/.config/mimeapps.list"

    # Git
    link "$DOTFILES_DIR/gitconfig" "$HOME/.gitconfig"

    echo ""
}

# Install cliphist (custom clipboard manager)
install_cliphist() {
    echo -e "${CYAN}━━━ Installing cliphist ━━━${NC}"
    
    mkdir -p "$HOME/.local/bin"
    mkdir -p "$HOME/.config/cliphist"
    mkdir -p "$HOME/.config/systemd/user"
    mkdir -p "$HOME/.config/fish/conf.d"
    mkdir -p "$HOME/.config/environment.d"
    
    # Install scripts
    cp "$DOTFILES_DIR/cliphist/cliphist.py" "$HOME/.local/bin/cliphist"
    cp "$DOTFILES_DIR/cliphist/cliphist-gui.py" "$HOME/.local/bin/cliphist-gui"
    cp "$DOTFILES_DIR/cliphist/cliphist-open" "$HOME/.local/bin/cliphist-open" 2>/dev/null || true
    chmod +x "$HOME/.local/bin/cliphist" "$HOME/.local/bin/cliphist-gui" "$HOME/.local/bin/cliphist-open" 2>/dev/null || true
    
    # Create default config
    if [ ! -f "$HOME/.config/cliphist/config.json" ]; then
        cat > "$HOME/.config/cliphist/config.json" << 'EOF'
{
  "max_items": 500,
  "max_display_len": 80,
  "ignore_duplicates": true
}
EOF
    fi
    
    # Install systemd service
    cp "$DOTFILES_DIR/cliphist/cliphist.service" "$HOME/.config/systemd/user/cliphist.service"
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable --now cliphist.service 2>/dev/null || true
    
    # Add ~/.local/bin to PATH (fish)
    if [ ! -f "$HOME/.config/fish/conf.d/path.fish" ]; then
        echo 'fish_add_path -g ~/.local/bin' > "$HOME/.config/fish/conf.d/path.fish"
    fi
    
    # Add ~/.local/bin to PATH (systemd/niri)
    if [ ! -f "$HOME/.config/environment.d/path.conf" ]; then
        echo 'PATH="${HOME}/.local/bin:${PATH}"' > "$HOME/.config/environment.d/path.conf"
    fi
    
    info "cliphist installed to ~/.local/bin/"
    info "Keybind: Mod+V → cliphist-gui"
    echo ""
}

# Set fish as default shell
setup_shell() {
    if [ "$SHELL" != "/usr/bin/fish" ]; then
        info "Setting fish as default shell..."
        chsh -s /usr/bin/fish
        info "Fish set as default shell"
    else
        info "Fish is already default shell"
    fi
}

# Main
main() {
    echo ""
    echo "=================================="
    echo "   Dotfiles Installer"
    echo "   github.com/animesao/dotfiles"
    echo "=================================="
    echo ""
    
    if [ ! -f "$DOTFILES_DIR/install.sh" ]; then
        error "Please run this script from the dotfiles directory"
        exit 1
    fi
    
    # Check and install packages
    read -p "Check and install missing packages? (y/N): " install_pkgs
    if [[ "$install_pkgs" =~ ^[Yy]$ ]]; then
        check_and_install
    fi
    
    # Setup configs
    read -p "Setup config symlinks? (y/N): " setup_cfgs
    if [[ "$setup_cfgs" =~ ^[Yy]$ ]]; then
        setup_configs
    fi
    
    # Install cliphist
    read -p "Install cliphist (clipboard manager)? (y/N): " install_clip
    if [[ "$install_clip" =~ ^[Yy]$ ]]; then
        install_cliphist
    fi
    
    # Setup shell
    read -p "Set fish as default shell? (y/N): " setup_fish
    if [[ "$setup_fish" =~ ^[Yy]$ ]]; then
        setup_shell
    fi

    # Install SDDM config + theme
    if [ -f "$DOTFILES_DIR/sddm/install.sh" ]; then
        read -p "Install SDDM config + theme? (y/N): " install_sddm
        if [[ "$install_sddm" =~ ^[Yy]$ ]]; then
            bash "$DOTFILES_DIR/sddm/install.sh"
        fi
    fi

    # Install screenshot utility
    if [ -f "$DOTFILES_DIR/screenshot/install.sh" ]; then
        read -p "Install screenshot utility? (y/N): " install_screenshot
        if [[ "$install_screenshot" =~ ^[Yy]$ ]]; then
            bash "$DOTFILES_DIR/screenshot/install.sh"
        fi
    fi
    
    echo ""
    info "Installation complete!"
    [ -d "$BACKUP_DIR" ] && info "Backup saved to: $BACKUP_DIR"
    echo ""
    info "Log out and log back in for changes to take effect."
    echo ""
}

main "$@"
