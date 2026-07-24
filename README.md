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
| GTK Theme | Adwaita |

## What's Included

- **niri/** - Tiling Wayland compositor (keybinds, layout, animations, display, rules)
- **noctalia/** - Shell with bar, dock, system monitor, color scheme (Gruvbox)
- **alacritty/** - Terminal config
- **fish/** - Shell with rustup integration
- **htop/** - System monitor config
- **micro/** - Text editor with Catppuccin themes
- **gtk-3.0/** - GTK settings

## Install

```bash
git clone https://github.com/animesao/dotfiles.git
cd dotfiles
chmod +x install.sh
./install.sh
```

The installer will:
1. Ask to install required packages (niri, alacritty, fish, htop, micro, btop)
2. Symlink all configs to `~/.config/`
3. Ask to set fish as default shell
4. Backup existing configs to `~/.dotfiles-backup/`

## Manual Steps

After install:

1. Log out and log back in
2. Select **niri** as session on the login screen
3. Adjust display/monitor settings in noctalia if needed
4. Install AUR packages manually if yay is not available

## Keybinds (niri)

| Key | Action |
|-----|--------|
| `Super + Enter` | Terminal (Alacritty) |
| `Super + Q` | Close window |
| `Super + Arrows` | Move focus |
| `Super + Shift + Arrows` | Move window |
| `Super + 1-9` | Switch workspace |
| `Super + Shift + 1-9` | Move to workspace |

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
│   ├── colors.json
│   ├── plugins.json
│   └── colorschemes/
├── alacritty/
├── fish/
├── htop/
├── micro/
└── gtk-3.0/
```
