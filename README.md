# Dotfiles

My personal dotfiles for CachyOS with niri (Wayland) + Noctalia Shell.

## What's Included

- **niri** - Tiling Wayland compositor
- **noctalia** - Shell with bar, dock, system monitor
- **alacritty** - Terminal emulator
- **fish** - Shell
- **htop** - System monitor
- **micro** - Text editor
- **gtk-3.0** - GTK theme settings

## Installation

```bash
git clone https://github.com/yourusername/dotfiles.git
cd dotfiles
chmod +x install.sh
./install.sh
```

## Structure

```
dotfiles/
├── install.sh          # Installer script
├── niri/               # Window manager config
├── noctalia/           # Shell/bar config
├── alacritty/          # Terminal config
├── fish/               # Shell config
├── htop/               # System monitor config
├── micro/              # Text editor config
└── gtk-3.0/            # GTK theme
```

## Manual Steps

After running the installer:

1. Log out and log back in
2. Select niri as your session in the login screen
3. Adjust display settings in noctalia if needed
4. Install AUR packages manually if yay is not available
# dotfiles
