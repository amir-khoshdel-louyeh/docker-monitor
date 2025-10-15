# Setup Tools Directory

This directory contains files needed for package installation and desktop integration.

## Files

### Core Installation Files
- **`docker-monitor-manager.desktop`** - Desktop entry file for Linux application menu
- **`post_install.py`** - Post-installation script that sets up desktop integration

### Helper Scripts
- **`create_icons.sh`** - Automated script to generate all required icon sizes from a source image
- **`TEST_ICONS.md`** - Commands to test if icons are properly installed

### Icons Directory
- **`icons/`** - Place all application icons here
  - See `icons/README.md` for detailed icon specifications
  - Required files:
    - `docker-monitor-manager-{16,32,48,64,128,256,512}x{16,32,48,64,128,256,512}.png`
    - `docker-monitor-manager.svg` (optional but recommended)

## How It Works

1. When you run `pip install .` or `pip install -e .`:
   - The package is installed
   - `post_install.py` is automatically executed

2. `post_install.py` does the following:
   - Copies the `.desktop` file to `~/.local/share/applications/`
   - Copies icons to `~/.local/share/icons/hicolor/{size}/apps/`
   - Updates the desktop database
   - Updates the icon cache

3. After logging out and back in:
   - The application appears in your system menu
   - You can search for "Docker Monitor Manager"
   - The application has proper icons

## Quick Start

1. Add your icon files to `icons/` directory:
   ```bash
   # Option 1: Use the helper script
   ./create_icons.sh /path/to/your/logo.png
   
   # Option 2: Manually copy your pre-made icons
   cp /path/to/icons/*.png icons/
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

3. Update system caches:
   ```bash
   update-desktop-database ~/.local/share/applications
   gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor
   ```

4. Log out and log back in

5. Search for "Docker Monitor Manager" in your application menu

## Platform Support

- **Linux**: Full support (GNOME, KDE, XFCE, etc.)
- **macOS**: Command-line only (desktop integration not implemented yet)
- **Windows**: Basic support (requires `pywin32` and `winshell` packages)

## Troubleshooting

See `TEST_ICONS.md` for commands to verify proper installation.
