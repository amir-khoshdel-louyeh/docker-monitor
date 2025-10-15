#!/bin/bash
# Post-install script for Docker Monitor Manager
# This script installs the .desktop file and icon to make the app searchable

set -e

echo "Installing Docker Monitor Manager desktop entry and icon..."

# Find the installed package location
PACKAGE_PATH=$(python3 -c "import docker_monitor; import os; print(os.path.dirname(docker_monitor.__file__))" 2>/dev/null || echo "")

if [ -z "$PACKAGE_PATH" ]; then
    echo "Error: Could not find docker_monitor package. Please install it first."
    exit 1
fi

# Create directories if they don't exist
LOCAL_SHARE="$HOME/.local/share"
APPLICATIONS_DIR="$LOCAL_SHARE/applications"
ICONS_DIR="$LOCAL_SHARE/icons/hicolor/512x512/apps"

mkdir -p "$APPLICATIONS_DIR"
mkdir -p "$ICONS_DIR"

# Copy desktop file
DESKTOP_FILE="$PACKAGE_PATH/docker-monitor-manager.desktop"
if [ -f "$DESKTOP_FILE" ]; then
    cp "$DESKTOP_FILE" "$APPLICATIONS_DIR/"
    chmod +x "$APPLICATIONS_DIR/docker-monitor-manager.desktop"
    echo "✓ Desktop entry installed to $APPLICATIONS_DIR"
else
    echo "Warning: Desktop file not found at $DESKTOP_FILE"
fi

# Copy icon
ICON_FILE="$PACKAGE_PATH/assets/logo.png"
if [ -f "$ICON_FILE" ]; then
    cp "$ICON_FILE" "$ICONS_DIR/docker-monitor-manager.png"
    echo "✓ Icon installed to $ICONS_DIR"
else
    echo "Warning: Icon file not found at $ICON_FILE"
fi

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$APPLICATIONS_DIR" 2>/dev/null || true
    echo "✓ Desktop database updated"
fi

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t "$LOCAL_SHARE/icons/hicolor" 2>/dev/null || true
    echo "✓ Icon cache updated"
fi

echo ""
echo "✓ Installation complete!"
echo "You can now search for 'Docker Monitor Manager' in your application menu."
echo ""
echo "If the app doesn't appear immediately, try:"
echo "  - Logging out and back in"
echo "  - Or run: killall -HUP nautilus (for GNOME)"
echo "  - Or run: kbuildsycoca5 (for KDE)"
