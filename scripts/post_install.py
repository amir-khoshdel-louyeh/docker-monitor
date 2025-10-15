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
    icons_dir = local_share / "icons" / "hicolor" / "512x512" / "apps"
    
    applications_dir.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy desktop file
    desktop_file = package_path / "docker-monitor-manager.desktop"
    if desktop_file.exists():
        dest = applications_dir / "docker-monitor-manager.desktop"
        shutil.copy2(desktop_file, dest)
        dest.chmod(0o755)
        print(f"✓ Desktop entry installed to {dest}")
    else:
        print(f"Warning: Desktop file not found at {desktop_file}")
    
    # Copy icon
    icon_file = package_path / "assets" / "logo.png"
    if icon_file.exists():
        dest = icons_dir / "docker-monitor-manager.png"
        shutil.copy2(icon_file, dest)
        print(f"✓ Icon installed to {dest}")
    else:
        print(f"Warning: Icon file not found at {icon_file}")
    
    # Update desktop database
    try:
        import subprocess
        subprocess.run(
            ["update-desktop-database", str(applications_dir)],
            capture_output=True,
            check=False
        )
        print("✓ Desktop database updated")
    except Exception:
        pass
    
    # Update icon cache
    try:
        import subprocess
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", str(local_share / "icons" / "hicolor")],
            capture_output=True,
            check=False
        )
        print("✓ Icon cache updated")
    except Exception:
        pass


def install_macos():
    """Install app bundle on macOS"""
    print("macOS Installation:")
    print("  - The command-line tools (docker-monitor-manager, dmm) are installed")
    print("  - To create a macOS app bundle, you would need to:")
    print("    1. Create a .app bundle structure")
    print("    2. Use py2app or similar tool")
    print("  - For now, you can run the app from terminal: docker-monitor-manager")


def install_windows():
    """Install shortcuts on Windows"""
    package_path = get_package_path()
    
    try:
        # Try to create a Start Menu shortcut
        import winshell
        from win32com.client import Dispatch
        
        # Get Start Menu path
        start_menu = Path(winshell.start_menu())
        shortcut_path = start_menu / "Docker Monitor Manager.lnk"
        
        # Find Python executable
        python_exe = sys.executable
        script_path = shutil.which("docker-monitor-manager")
        
        if script_path:
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = script_path
            shortcut.WorkingDirectory = str(Path.home())
            
            # Set icon if available
            icon_file = package_path / "assets" / "logo.png"
            if icon_file.exists():
                # Convert PNG to ICO if possible
                try:
                    from PIL import Image
                    ico_path = package_path / "assets" / "logo.ico"
                    img = Image.open(icon_file)
                    img.save(ico_path, format='ICO')
                    shortcut.IconLocation = str(ico_path)
                except Exception:
                    pass
            
            shortcut.save()
            print(f"✓ Start Menu shortcut created at {shortcut_path}")
        else:
            print("Warning: Could not find docker-monitor-manager executable")
            
    except ImportError:
        print("Windows Installation:")
        print("  - The command-line tools (docker-monitor-manager, dmm) are installed")
        print("  - To create Start Menu shortcuts, install: pip install pywin32 winshell")
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
