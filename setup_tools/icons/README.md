# Icons for Docker Monitor Manager

## Required Icon Files for All Platforms

### Linux (PNG + SVG)

Create PNG icons with the following exact filenames and dimensions:

1. **docker-monitor-manager-16x16.png** (16×16 pixels) ✅
2. **docker-monitor-manager-32x32.png** (32×32 pixels) ✅
3. **docker-monitor-manager-48x48.png** (48×48 pixels) ⭐ Critical
4. **docker-monitor-manager-64x64.png** (64×64 pixels) ✅
5. **docker-monitor-manager-128x128.png** (128×128 pixels) ✅
6. **docker-monitor-manager-256x256.png** (256×256 pixels) ✅
7. **docker-monitor-manager-512x512.png** (512×512 pixels) ⭐ Critical
8. **docker-monitor-manager.svg** (Scalable Vector Graphics) ⭐ Recommended

### Windows (ICO)

9. **docker-monitor-manager.ico** (Multi-resolution ICO file) ⭐ Required for Windows

This file contains multiple resolutions (16, 32, 48, 64, 128, 256) in one file.

### macOS (ICNS)

10. **docker-monitor-manager.icns** (Apple Icon Image) ⭐ Required for macOS

This file contains multiple resolutions for macOS Finder and Dock.

## Current Status

All required icon files are present:
- ✅ 7 PNG files (Linux)
- ✅ 1 SVG file (Linux - scalable)
- ✅ 1 ICO file (Windows)
- ✅ 1 ICNS file (macOS)

**Total: 10 icon files for cross-platform support**

## Icon Design Guidelines

- **Theme**: Docker/Container related (whale, container boxes, etc.)
- **Style**: Modern, clean, professional
- **Colors**: Use Docker's blue (#0db7ed) as primary color or similar tech colors
- **Background**: Transparent (PNG with alpha channel)
- **Format**: 
  - PNG: 24-bit or 32-bit with alpha transparency
  - SVG: Clean vector paths, no embedded raster images

## Minimum Required

At minimum, you need:
- **docker-monitor-manager-48x48.png** (for most desktop environments)
- **docker-monitor-manager-512x512.png** (for high-resolution displays)
- **docker-monitor-manager.svg** (optional, for scalability)

## Icon Placement After Installation

On Linux systems, icons will be installed to:
```
~/.local/share/icons/hicolor/{size}/apps/docker-monitor-manager.png
```

Where `{size}` is one of: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256, 512x512, or scalable (for SVG).

## Testing Icons

After creating icons and reinstalling the package:

1. Run: `update-desktop-database ~/.local/share/applications`
2. Run: `gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor`
3. Log out and log back in (or restart your desktop environment)
4. Search for "Docker Monitor Manager" in your application menu

## Icon Creation Tools

- **GIMP**: Free, open-source image editor
- **Inkscape**: Free, open-source vector graphics editor (for SVG)
- **Online tools**: 
  - https://www.iloveimg.com/resize-image
  - https://icon-icons.com/
  - https://www.flaticon.com/

## Example Icon Ideas

- Docker whale logo with a monitoring screen
- Container boxes with a magnifying glass
- Terminal window with Docker logo
- Graph/chart with container icon
- Modern geometric design with Docker blue colors
