#!/usr/bin/env python3
"""
Complete uninstaller for Docker Monitor Manager
Removes all installed files, icons, desktop entries, and the package itself
"""

import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path


def print_header():
    """Print uninstaller header"""
    print("\n" + "=" * 70)
    print("Docker Monitor Manager - Complete Uninstaller")
    print("=" * 70 + "\n")


def confirm_uninstall():
    """Ask user for confirmation"""
    print("⚠️  This will completely remove Docker Monitor Manager including:")
    print("   - Application package")
    print("   - Desktop entry (.desktop file)")
    print("   - All icons")
    print("   - Configuration files (optional)")
    print()
    
    response = input("Are you sure you want to continue? [y/N]: ").strip().lower()
    if response not in ['y', 'yes']:
        print("\n❌ Uninstall cancelled.")
        sys.exit(0)
    print()


def remove_linux_files():
    """Remove Linux-specific files (desktop entry, icons)"""
    removed_files = []
    
    home = Path.home()
    local_share = home / ".local" / "share"
    
    # Remove desktop entry
    desktop_file = local_share / "applications" / "docker-monitor-manager.desktop"
    if desktop_file.exists():
        try:
            desktop_file.unlink()
            removed_files.append(str(desktop_file))
            print(f"✓ Removed desktop entry: {desktop_file}")
        except Exception as e:
            print(f"✗ Failed to remove {desktop_file}: {e}")
    
    # Remove icons
    icons_base = local_share / "icons" / "hicolor"
    if icons_base.exists():
        for size_dir in icons_base.iterdir():
            if size_dir.is_dir():
                apps_dir = size_dir / "apps"
                if apps_dir.exists():
                    # Remove PNG icons
                    icon_file = apps_dir / "docker-monitor-manager.png"
                    if icon_file.exists():
                        try:
                            icon_file.unlink()
                            removed_files.append(str(icon_file))
                            print(f"✓ Removed icon: {icon_file}")
                        except Exception as e:
                            print(f"✗ Failed to remove {icon_file}: {e}")
                    
                    # Remove SVG icons
                    icon_svg = apps_dir / "docker-monitor-manager.svg"
                    if icon_svg.exists():
                        try:
                            icon_svg.unlink()
                            removed_files.append(str(icon_svg))
                            print(f"✓ Removed icon: {icon_svg}")
                        except Exception as e:
                            print(f"✗ Failed to remove {icon_svg}: {e}")
    
    # Update desktop database
    try:
        applications_dir = local_share / "applications"
        subprocess.run(
            ["update-desktop-database", str(applications_dir)],
            capture_output=True,
            check=False
        )
        print("✓ Updated desktop database")
    except Exception:
        pass
    
    # Update icon cache
    try:
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", str(icons_base)],
            capture_output=True,
            check=False
        )
        print("✓ Updated icon cache")
    except Exception:
        pass
    
    return removed_files


def remove_windows_files():
    """Remove Windows-specific files (shortcuts, icons)"""
    removed_files = []
    
    try:
        # Remove icon from user directory
        home = Path.home()
        icon_dir = home / ".icons"
        icon_file = icon_dir / "docker-monitor-manager.ico"
        
        if icon_file.exists():
            try:
                icon_file.unlink()
                removed_files.append(str(icon_file))
                print(f"✓ Removed icon: {icon_file}")
            except Exception as e:
                print(f"✗ Failed to remove {icon_file}: {e}")
        
        # Try to remove Start Menu shortcut
        try:
            import winshell
            start_menu = Path(winshell.start_menu())
            shortcut_path = start_menu / "Docker Monitor Manager.lnk"
            
            if shortcut_path.exists():
                shortcut_path.unlink()
                removed_files.append(str(shortcut_path))
                print(f"✓ Removed Start Menu shortcut: {shortcut_path}")
        except ImportError:
            print("ℹ️  winshell not available, skipping Start Menu shortcut removal")
        except Exception as e:
            print(f"✗ Failed to remove Start Menu shortcut: {e}")
            
    except Exception as e:
        print(f"✗ Error removing Windows files: {e}")
    
    return removed_files


def remove_macos_files():
    """Remove macOS-specific files (icons)"""
    removed_files = []
    
    try:
        home = Path.home()
        icon_dir = home / "Library" / "Icons"
        icon_file = icon_dir / "docker-monitor-manager.icns"
        
        if icon_file.exists():
            try:
                icon_file.unlink()
                removed_files.append(str(icon_file))
                print(f"✓ Removed icon: {icon_file}")
            except Exception as e:
                print(f"✗ Failed to remove {icon_file}: {e}")
    except Exception as e:
        print(f"✗ Error removing macOS files: {e}")
    
    return removed_files


def remove_config_files():
    """Remove configuration files (optional)"""
    response = input("\n❓ Do you want to remove configuration files? [y/N]: ").strip().lower()
    
    if response not in ['y', 'yes']:
        print("ℹ️  Keeping configuration files")
        return []
    
    removed_files = []
    home = Path.home()
    
    # Common config locations
    config_paths = [
        home / ".config" / "docker-monitor-manager",
        home / ".docker-monitor-manager",
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                if config_path.is_file():
                    config_path.unlink()
                elif config_path.is_dir():
                    shutil.rmtree(config_path)
                removed_files.append(str(config_path))
                print(f"✓ Removed config: {config_path}")
            except Exception as e:
                print(f"✗ Failed to remove {config_path}: {e}")
    
    return removed_files


def remove_executables():
    """Remove executable scripts from bin directories"""
    removed_files = []
    
    # List of executables to remove
    executables = [
        "docker-monitor-manager",
        "dmm",
        "dmm-config",
        "dmm-doctor",
        "dmm-test",
        "dmm-uninstall",
    ]
    
    # Common bin directories
    bin_dirs = []
    
    # User bin directory
    home = Path.home()
    bin_dirs.append(home / ".local" / "bin")
    
    # pipx bin directory
    pipx_bin = home / ".local" / "bin"
    if pipx_bin.exists():
        bin_dirs.append(pipx_bin)
    
    # System-wide (if we have permission)
    if os.geteuid() == 0 if hasattr(os, 'geteuid') else False:
        bin_dirs.extend([
            Path("/usr/local/bin"),
            Path("/usr/bin"),
        ])
    
    print("\n🗑️  Removing executable scripts...")
    
    for bin_dir in bin_dirs:
        if not bin_dir.exists():
            continue
            
        for exe_name in executables:
            exe_path = bin_dir / exe_name
            if exe_path.exists():
                try:
                    exe_path.unlink()
                    removed_files.append(str(exe_path))
                    print(f"✓ Removed executable: {exe_path}")
                except Exception as e:
                    print(f"✗ Failed to remove {exe_path}: {e}")
    
    if not removed_files:
        print("ℹ️  No executable scripts found to remove")
    
    return removed_files


def uninstall_package():
    """Uninstall the Python package"""
    print("\n🗑️  Uninstalling Python package...")
    
    package_uninstalled = False
    
    # Try to detect if installed with pipx
    try:
        result = subprocess.run(
            ["pipx", "list"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0 and "docker-monitor-manager" in result.stdout:
            print("ℹ️  Detected pipx installation")
            result = subprocess.run(
                ["pipx", "uninstall", "docker-monitor-manager"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✓ Package uninstalled successfully (pipx)")
                # Also remove any remaining executables
                remove_executables()
                return True
            else:
                print(f"✗ Failed to uninstall with pipx: {result.stderr}")
                # Continue to try pip
    except FileNotFoundError:
        # pipx not installed, skip
        pass
    except Exception as e:
        print(f"ℹ️  Could not check pipx: {e}")
    
    # Try with pip3
    for pip_cmd in ["pip3", "pip"]:
        try:
            # Check if package is installed with this pip
            check_result = subprocess.run(
                [pip_cmd, "show", "docker-monitor-manager"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if check_result.returncode == 0:
                print(f"ℹ️  Detected {pip_cmd} installation")
                
                # Try with --break-system-packages for newer pip versions
                result = subprocess.run(
                    [pip_cmd, "uninstall", "-y", "--break-system-packages", "docker-monitor-manager"],
                    capture_output=True,
                    text=True
                )
                
                # If --break-system-packages not supported, try without it
                if result.returncode != 0 and "--break-system-packages" in result.stderr:
                    result = subprocess.run(
                        [pip_cmd, "uninstall", "-y", "docker-monitor-manager"],
                        capture_output=True,
                        text=True
                    )
                
                if result.returncode == 0:
                    print(f"✓ Package uninstalled successfully ({pip_cmd})")
                    # Also remove executable scripts (especially for editable installs)
                    remove_executables()
                    return True
                else:
                    print(f"✗ Failed to uninstall with {pip_cmd}: {result.stderr}")
                    
        except FileNotFoundError:
            # This pip command not available
            continue
        except Exception as e:
            print(f"ℹ️  Could not use {pip_cmd}: {e}")
            continue
    
    # Try with python -m pip as fallback
    try:
        # Try with --break-system-packages first
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "--break-system-packages", "docker-monitor-manager"],
            capture_output=True,
            text=True
        )
        
        # If --break-system-packages not supported, try without it
        if result.returncode != 0 and "--break-system-packages" in result.stderr:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", "docker-monitor-manager"],
                capture_output=True,
                text=True
            )
        
        if result.returncode == 0:
            print("✓ Package uninstalled successfully (python -m pip)")
            # Also remove executable scripts
            remove_executables()
            return True
        else:
            print(f"✗ Failed to uninstall package: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error uninstalling package: {e}")
        return False


def main():
    """Main uninstaller function"""
    print_header()
    
    # Confirm uninstall
    confirm_uninstall()
    
    # Detect platform
    system = platform.system()
    print(f"📋 Detected OS: {system}\n")
    
    all_removed_files = []
    
    # Remove platform-specific files
    if system == "Linux":
        print("🐧 Removing Linux files...")
        removed = remove_linux_files()
        all_removed_files.extend(removed)
        
    elif system == "Windows":
        print("🪟 Removing Windows files...")
        removed = remove_windows_files()
        all_removed_files.extend(removed)
        
    elif system == "Darwin":  # macOS
        print("🍎 Removing macOS files...")
        removed = remove_macos_files()
        all_removed_files.extend(removed)
    
    # Remove config files (optional)
    config_removed = remove_config_files()
    all_removed_files.extend(config_removed)
    
    # Uninstall the package
    package_uninstalled = uninstall_package()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Uninstall Summary")
    print("=" * 70)
    print(f"✓ Removed {len(all_removed_files)} file(s)")
    print(f"{'✓' if package_uninstalled else '✗'} Package uninstalled")
    
    if system == "Linux":
        print("\n💡 Note: You may need to log out and log back in for changes to")
        print("   take full effect in the application menu.")
    
    print("\n✅ Uninstall complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Uninstall interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
