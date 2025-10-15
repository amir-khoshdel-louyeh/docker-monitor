#!/usr/bin/env python3
"""
Post-installation script for Docker Monitor Manager
This script installs desktop entry and icon across different platforms
"""

import os
import sys
import shutil
import platform
from pathlib import Path


def get_package_path():
    """Find the installed package location"""
    try:
        import docker_monitor
        return Path(docker_monitor.__file__).parent
    except ImportError:
        print("Error: Could not find docker_monitor package. Please install it first.")
        sys.exit(1)


def install_linux():
    """Install desktop entry and icon on Linux"""
    package_path = get_package_path()
    
    # Setup directories
    local_share = Path.home() / ".local" / "share"
    applications_dir = local_share / "applications"
    
    applications_dir.mkdir(parents=True, exist_ok=True)
    
    # Get the setup_tools directory (where this script and desktop file are)
    setup_tools_dir = Path(__file__).parent
    desktop_file = setup_tools_dir / "docker-monitor-manager.desktop"
    
    # Copy desktop file
    if desktop_file.exists():
        dest = applications_dir / "docker-monitor-manager.desktop"
        shutil.copy2(desktop_file, dest)
        dest.chmod(0o644)
        print(f"✓ Desktop entry installed to {dest}")
    else:
        print(f"Warning: Desktop file not found at {desktop_file}")
    
    # Install icons in multiple sizes
    icon_sizes = {
        "16x16": 16,
        "32x32": 32,
        "48x48": 48,
        "64x64": 64,
        "128x128": 128,
        "256x256": 256,
        "512x512": 512,
        "scalable": None  # For SVG
    }
    
    icons_installed = False
    icons_base = local_share / "icons" / "hicolor"
    
    for size_dir, size in icon_sizes.items():
        if size_dir == "scalable":
            # Try to install SVG icon
            apps_dir = icons_base / size_dir / "apps"
            apps_dir.mkdir(parents=True, exist_ok=True)
            
            # Look for SVG icon in setup_tools/icons
            svg_icon = setup_tools_dir / "icons" / "docker-monitor-manager.svg"
            if svg_icon.exists():
                dest = apps_dir / "docker-monitor-manager.svg"
                shutil.copy2(svg_icon, dest)
                print(f"✓ Icon installed to {dest}")
                icons_installed = True
        else:
            # Install PNG icons
            apps_dir = icons_base / size_dir / "apps"
            apps_dir.mkdir(parents=True, exist_ok=True)
            
            # Look for PNG icon in setup_tools/icons
            png_icon = setup_tools_dir / "icons" / f"docker-monitor-manager-{size}x{size}.png"
            if png_icon.exists():
                dest = apps_dir / "docker-monitor-manager.png"
                shutil.copy2(png_icon, dest)
                print(f"✓ Icon ({size}x{size}) installed to {dest}")
                icons_installed = True
    
    if not icons_installed:
        print("Warning: No icons found in setup_tools/icons/")
    
    # Update desktop database
    try:
        import subprocess
        result = subprocess.run(
            ["update-desktop-database", str(applications_dir)],
            capture_output=True,
            check=False
        )
        if result.returncode == 0:
            print("✓ Desktop database updated")
        else:
            print("Note: Could not update desktop database (this is usually fine)")
    except Exception as e:
        print(f"Note: Could not update desktop database: {e}")
    
    # Update icon cache
    try:
        import subprocess
        result = subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", str(local_share / "icons" / "hicolor")],
            capture_output=True,
            check=False
        )
        if result.returncode == 0:
            print("✓ Icon cache updated")
        else:
            # Try xdg-icon-resource as alternative
            result2 = subprocess.run(
                ["xdg-icon-resource", "forceupdate"],
                capture_output=True,
                check=False
            )
            if result2.returncode == 0:
                print("✓ Icon cache updated (using xdg-icon-resource)")
            else:
                print("Note: Could not update icon cache (this is usually fine)")
    except Exception as e:
        print(f"Note: Could not update icon cache: {e}")


def install_macos():
    """Install app bundle on macOS"""
    package_path = get_package_path()
    setup_tools_dir = Path(__file__).parent
    
    # Try to install icon to user's icon directory
    try:
        home = Path.home()
        icon_dir = home / "Library" / "Icons"
        icon_dir.mkdir(parents=True, exist_ok=True)
        
        # Look for ICNS icon
        icns_icon = setup_tools_dir / "icons" / "docker-monitor-manager.icns"
        if icns_icon.exists():
            dest = icon_dir / "docker-monitor-manager.icns"
            shutil.copy2(icns_icon, dest)
            print(f"✓ Icon installed to {dest}")
        else:
            print("Note: ICNS icon not found, icon will not be available")
            
    except Exception as e:
        print(f"Note: Could not install icon: {e}")
    
    print("\nmacOS Installation:")
    print("  ✓ The command-line tools (docker-monitor-manager, dmm) are installed")
    print("  - To create a macOS app bundle, you would need to:")
    print("    1. Create a .app bundle structure")
    print("    2. Use py2app or similar tool")
    print("  - For now, you can run the app from terminal: docker-monitor-manager")


def install_windows():
    """Install shortcuts on Windows"""
    package_path = get_package_path()
    setup_tools_dir = Path(__file__).parent
    
    # Try to copy icon to a user-accessible location
    try:
        home = Path.home()
        icon_dir = home / ".icons"
        icon_dir.mkdir(parents=True, exist_ok=True)
        
        # Look for ICO icon
        ico_icon = setup_tools_dir / "icons" / "docker-monitor-manager.ico"
        if ico_icon.exists():
            dest = icon_dir / "docker-monitor-manager.ico"
            shutil.copy2(ico_icon, dest)
            print(f"✓ Icon installed to {dest}")
    except Exception as e:
        print(f"Note: Could not install icon: {e}")
    
    try:
        # Try to create a Start Menu shortcut
        import winshell
        from win32com.client import Dispatch
        
        # Get Start Menu path
        start_menu = Path(winshell.start_menu())
        shortcut_path = start_menu / "Docker Monitor Manager.lnk"
        
        # Find Python executable and icon
        python_exe = sys.executable
        script_path = shutil.which("docker-monitor-manager")
        icon_path = str(home / ".icons" / "docker-monitor-manager.ico")
        
        if script_path:
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = script_path
            shortcut.WorkingDirectory = str(Path.home())
            
            # Set icon if available
            if Path(icon_path).exists():
                shortcut.IconLocation = icon_path
            
            shortcut.save()
            print(f"✓ Start Menu shortcut created at {shortcut_path}")
        else:
            print("Warning: Could not find docker-monitor-manager executable")
            
    except ImportError:
        print("\nWindows Installation:")
        print("  ✓ The command-line tools (docker-monitor-manager, dmm) are installed")
        print("  - To create Start Menu shortcuts with icons, install:")
        print("    pip install pywin32 winshell")
        print("  - For now, you can run the app from terminal: docker-monitor-manager")
    except Exception as e:
        print(f"Note: Could not create Windows shortcut: {e}")
        print("  - You can still run the app from terminal: docker-monitor-manager")


def main():
    """Main installation function"""
    print("\n" + "=" * 60)
    print("Docker Monitor Manager - Post Installation")
    print("=" * 60 + "\n")
    
    system = platform.system()
    
    if system == "Linux":
        install_linux()
        print("\n✓ Installation complete!")
        print("You can now search for 'Docker Monitor Manager' in your application menu.")
        print("\nIf the app doesn't appear immediately, try:")
        print("  - Logging out and back in")
        print("  - Or run: killall -HUP nautilus (for GNOME)")
        print("  - Or run: kbuildsycoca5 (for KDE)")
        
    elif system == "Darwin":  # macOS
        install_macos()
        print("\n✓ Command-line installation complete!")
        print("Run the app with: docker-monitor-manager")
        
    elif system == "Windows":
        install_windows()
        print("\n✓ Installation complete!")
        print("Run the app with: docker-monitor-manager")
        
    else:
        print(f"Platform '{system}' is not fully supported yet.")
        print("You can still run the app from terminal: docker-monitor-manager")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
