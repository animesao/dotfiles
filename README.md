# Dotfiles

My personal dotfiles for CachyOS (Arch Linux) with niri + Noctalia Shell.

## Stack

| Component | App |
|-----------|-----|
| Compositor | niri (Wayland) |
| Shell/Bar | Noctalia Shell |
| Terminal | Alacritty |
| Shell | Fish |
| Editor | Micro |
| System Monitor | htop / btop |
| Clipboard | cliphist (custom) |
| GTK Theme | Gruvbox |

## What's Included

- **niri/** - Tiling Wayland compositor (keybinds, layout, animations, display, rules)
- **noctalia/** - Shell with bar, dock, system monitor, color scheme (Gruvbox)
- **alacritty/** - Terminal config
- **fish/** - Shell with rustup integration
- **htop/** - System monitor config
- **micro/** - Text editor with Catppuccin themes
- **gtk-3.0/** - GTK settings
- **cliphist/** - Custom clipboard manager (TUI + GUI)

## Install

```bash
git clone git@github.com:animesao/dotfiles.git
cd dotfiles
chmod +x install.sh
./install.sh
```

The installer will:
1. Check and install required packages (niri, alacritty, fish, htop, micro, btop, wl-clipboard)
2. Symlink all configs to `~/.config/`
3. Install cliphist (clipboard manager with history + search)
4. Set fish as default shell
5. Backup existing configs to `~/.dotfiles-backup/`

## cliphist

Custom clipboard manager for Wayland with history and search.

### Usage

```bash
cliphist          # Open TUI
cliphist-gui      # Open GUI (Gruvbox theme)
cliphist list     # List items
cliphist count    # Show count
cliphist clear    # Clear history
```

### Keybinds

| Key | Action |
|-----|--------|
| `Mod+V` | Open cliphist GUI |
| `Enter` | Copy selected |
| `/` | Search (TUI) |
| `Ctrl+F` | Focus search (GUI) |
| `Ctrl+P` | Pin/unpin |
| `Delete` | Delete item |
| `Esc` | Close |

### Features

- History tracking (text + images)
- Search with real-time filtering
- Pin important items
- TUI mode (terminal) + GUI mode (PyQt6, Gruvbox theme)
- Systemd daemon for background monitoring
- Preview panel in GUI

## Keybinds (niri)

| Key | Action |
|-----|--------|
| `Super + Enter` | Terminal (Alacritty) |
| `Super + Q` | Close window |
| `Super + Arrows` | Move focus |
| `Super + Shift + Arrows` | Move window |
| `Super + 1-9` | Switch workspace |
| `Super + Shift + 1-9` | Move to workspace |
| `Super + V` | Clipboard history (cliphist) |
| `Super + Shift + S` | Screenshot (hyprshot) |

See `niri/cfg/keybinds.kdl` for full list.

## Structure

```
dotfiles/
├── install.sh          # Installer
├── niri/
│   ├── config.kdl      # Main config
│   └── cfg/            # Split configs
│       ├── keybinds.kdl
│       ├── layout.kdl
│       ├── animation.kdl
│       ├── display.kdl
│       ├── input.kdl
│       ├── rules.kdl
│       ├── misc.kdl
│       └── autostart.kdl
├── noctalia/
│   ├── settings.json   # Main settings
│   ├── colors.json     # Gruvbox palette
│   ├── plugins.json
│   └── colorschemes/
├── alacritty/
├── fish/
├── htop/
├── micro/
├── gtk-3.0/
└── cliphist/
    ├── cliphist.py      # TUI + daemon
    ├── cliphist-gui.py  # PyQt6 GUI
    ├── cliphist.service  # Systemd service
    └── install.sh
```
