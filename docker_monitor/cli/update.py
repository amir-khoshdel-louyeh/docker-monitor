#!/usr/bin/env python3
"""
dmm-update: Update Docker Monitor Manager to the latest version

This tool updates the application to the latest version from PyPI or GitHub.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")


def print_success(text: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print an error message"""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print an info message"""
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print a warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def get_current_version() -> Optional[str]:
    """Get the currently installed version"""
    try:
        import docker_monitor
        return getattr(docker_monitor, '__version__', 'Unknown')
    except (ImportError, AttributeError):
        return None


def check_pip_available() -> bool:
    """Check if pip is available"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def get_latest_version() -> Optional[str]:
    """Get the latest version available on PyPI"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'index', 'versions', 'docker-monitor-manager'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            # Parse output to get latest version
            for line in result.stdout.split('\n'):
                if 'Available versions:' in line or 'LATEST:' in line:
                    # Extract version number
                    parts = line.split()
                    for part in parts:
                        if part[0].isdigit():
                            return part.rstrip(',')
        
        # Alternative method using pip show
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'show', 'docker-monitor-manager'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
        
        return None
    except Exception:
        return None


def update_package(force: bool = False) -> bool:
    """Update the package to the latest version"""
    print_info("Updating Docker Monitor Manager...")
    
    try:
        # Build the pip install command
        cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', 'docker-monitor-manager']
        
        if force:
            cmd.append('--force-reinstall')
        
        # Check if running with user flag (not in virtual env)
        in_virtualenv = (
            hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        )
        
        if not in_virtualenv and os.geteuid() != 0:
            cmd.insert(4, '--user')
        
        print_info(f"Running: {' '.join(cmd)}")
        print()
        
        # Run the update command
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            print()
            print_success("Docker Monitor Manager updated successfully!")
            
            # Run post-install setup
            print()
            print_info("Running post-installation setup...")
            setup_result = subprocess.run(
                [sys.executable, '-m', 'docker_monitor.cli.setup', 'post-install'],
                check=False
            )
            
            if setup_result.returncode == 0:
                print_success("Post-installation setup completed!")
            else:
                print_warning("Post-installation setup had issues. You can run 'dmm-setup' manually.")
            
            return True
        else:
            print()
            print_error("Failed to update Docker Monitor Manager!")
            return False
            
    except Exception as e:
        print_error(f"Error during update: {e}")
        return False


def main():
    """Main entry point for the update command"""
    print_header("Docker Monitor Manager - Update Tool")
    
    # Check if pip is available
    if not check_pip_available():
        print_error("pip is not available!")
        print_info("Please install pip first:")
        print_info("  sudo apt-get install python3-pip")
        sys.exit(1)
    
    # Get current version
    current_version = get_current_version()
    if current_version:
        print_info(f"Current version: {current_version}")
    else:
        print_warning("Could not determine current version")
    
    # Check for force flag
    force = '--force' in sys.argv or '-f' in sys.argv
    
    if force:
        print_warning("Force reinstall mode enabled")
    
    # Ask for confirmation
    print()
    try:
        response = input(f"{Colors.YELLOW}Do you want to update to the latest version? (y/N): {Colors.ENDC}")
        if response.lower() not in ['y', 'yes']:
            print_info("Update cancelled.")
            sys.exit(0)
    except KeyboardInterrupt:
        print()
        print_info("Update cancelled.")
        sys.exit(0)
    
    print()
    
    # Perform the update
    success = update_package(force=force)
    
    if success:
        print()
        print_header("Update Complete!")
        
        # Get new version
        new_version = get_current_version()
        if new_version and new_version != current_version:
            print_success(f"Updated from version {current_version} to {new_version}")
        elif new_version:
            print_success(f"Version {new_version} is installed")
        
        print()
        print_info("You can now run 'dmm' or 'docker-monitor-manager' to start the application.")
        print_info("Run 'dmm-help' to see all available commands.")
        sys.exit(0)
    else:
        print()
        print_error("Update failed!")
        print_info("You can try manually:")
        print_info(f"  {sys.executable} -m pip install --upgrade docker-monitor-manager")
        sys.exit(1)


if __name__ == "__main__":
    main()
