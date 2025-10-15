#!/usr/bin/env python3
"""
Setup CLI - Post-installation setup commands
"""

import sys
from pathlib import Path

def post_install():
    """Run post-installation setup (install desktop entry and icons)"""
    setup_tools_dir = Path(__file__).parent.parent.parent / "setup_tools"
    post_install_script = setup_tools_dir / "post_install.py"
    
    if post_install_script.exists():
        # Execute the post_install script
        import subprocess
        result = subprocess.run([sys.executable, str(post_install_script)])
        sys.exit(result.returncode)
    else:
        print(f"Error: Post-install script not found at {post_install_script}")
        print("Please run: python3 setup_tools/post_install.py")
        sys.exit(1)

def main():
    """Main entry point for setup commands"""
    if len(sys.argv) > 1 and sys.argv[1] == "post-install":
        post_install()
    else:
        print("Docker Monitor Manager - Setup Tools")
        print("")
        print("Available commands:")
        print("  dmm-setup post-install   Run post-installation setup")
        print("")
        print("Or you can directly run:")
        print("  python3 setup_tools/post_install.py")

if __name__ == "__main__":
    main()
