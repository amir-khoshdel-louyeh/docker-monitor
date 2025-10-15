#!/usr/bin/env python3
"""
Docker Monitor Manager - Uninstaller CLI
Command-line interface for complete uninstallation
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Run the uninstaller script"""
    try:
        # Get the path to uninstall.py
        # Try to find it in the installed package location
        try:
            import docker_monitor
            pkg_dir = Path(docker_monitor.__file__).parent.parent
            uninstall_script = pkg_dir / "setup_tools" / "uninstall.py"
        except:
            # Fallback: assume we're in development mode
            uninstall_script = Path(__file__).parent.parent.parent / "setup_tools" / "uninstall.py"
        
        if not uninstall_script.exists():
            print("❌ Error: Uninstall script not found!")
            print(f"   Expected location: {uninstall_script}")
            print()
            print("💡 Try running manually:")
            print("   python3 -m pip uninstall docker-monitor-manager")
            return 1
        
        # Run the uninstall script
        result = subprocess.run([sys.executable, str(uninstall_script)])
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n\n❌ Uninstall interrupted by user.")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
