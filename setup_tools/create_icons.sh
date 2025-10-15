#!/bin/bash
# Helper script to create all required icon sizes from a source image
# Usage: ./create_icons.sh <source-image-path>

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <source-image-path>"
    echo ""
    echo "Example: $0 my-logo.png"
    echo "Example: $0 my-logo.svg"
    echo ""
    echo "This script will create all required icon sizes in setup_tools/icons/"
    exit 1
fi

SOURCE_IMAGE="$1"

if [ ! -f "$SOURCE_IMAGE" ]; then
    echo "Error: Source image '$SOURCE_IMAGE' not found!"
    exit 1
fi

# Check if ImageMagick is installed
if ! command -v convert &> /dev/null; then
    echo "Error: ImageMagick is not installed!"
    echo "Please install it with: sudo apt install imagemagick"
    exit 1
fi

# Create icons directory if it doesn't exist
ICONS_DIR="setup_tools/icons"
mkdir -p "$ICONS_DIR"

echo "Creating icons from: $SOURCE_IMAGE"
echo "Output directory: $ICONS_DIR"
echo ""

# Array of required sizes
SIZES=(16 32 48 64 128 256 512)

# Create PNG icons for each size
for size in "${SIZES[@]}"; do
    output_file="$ICONS_DIR/docker-monitor-manager-${size}x${size}.png"
    echo "Creating ${size}x${size} icon..."
    convert "$SOURCE_IMAGE" -resize ${size}x${size} -background none -gravity center -extent ${size}x${size} "$output_file"
    echo "✓ Created: $output_file"
done

# If source is SVG, copy it directly
if [[ "$SOURCE_IMAGE" == *.svg ]]; then
    echo ""
    echo "Copying SVG source..."
    cp "$SOURCE_IMAGE" "$ICONS_DIR/docker-monitor-manager.svg"
    echo "✓ Created: $ICONS_DIR/docker-monitor-manager.svg"
fi

echo ""
echo "✓ All icons created successfully!"
echo ""
echo "Next steps:"
echo "1. Review the created icons in: $ICONS_DIR"
echo "2. Reinstall the package: pip install -e ."
echo "3. Update system caches:"
echo "   update-desktop-database ~/.local/share/applications"
echo "   gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor"
echo "4. Log out and log back in (or restart your desktop environment)"
