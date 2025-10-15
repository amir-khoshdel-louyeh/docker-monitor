#!/usr/bin/env python3
"""
dmm-doctor: Docker Monitor Manager system health checker and auto-fixer

This tool diagnoses common issues and automatically fixes them:
- Docker installation and service status
- Docker permissions
- AppArmor/SELinux conflicts
- Network connectivity
- Container runtime issues
- System resources
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from typing import List, Tuple


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


def run_command(cmd: List[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result"""
    try:
        if capture:
            return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        else:
            return subprocess.run(cmd, check=False)
    except FileNotFoundError:
        result = subprocess.CompletedProcess(cmd, returncode=127, stdout='', stderr='Command not found')
        return result


def print_header(text: str):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")


def print_check(name: str, status: bool, message: str = ""):
    """Print a check result"""
    icon = f"{Colors.GREEN}✓{Colors.ENDC}" if status else f"{Colors.RED}✗{Colors.ENDC}"
    status_text = f"{Colors.GREEN}OK{Colors.ENDC}" if status else f"{Colors.RED}FAIL{Colors.ENDC}"
    print(f"{icon} {name}: {status_text}")
    if message:
        print(f"  {Colors.YELLOW}→{Colors.ENDC} {message}")


def print_fix(message: str):
    """Print a fix action"""
    print(f"  {Colors.CYAN}🔧 FIX:{Colors.ENDC} {message}")


def check_docker_installed() -> Tuple[bool, str]:
    """Check if Docker is installed"""
    result = run_command(['docker', '--version'])
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, "Docker is not installed"


def check_docker_running() -> Tuple[bool, str]:
    """Check if Docker daemon is running"""
    result = run_command(['docker', 'ps'])
    if result.returncode == 0:
        return True, "Docker daemon is running"
    return False, f"Docker daemon is not running: {result.stderr.strip()}"


def check_docker_permissions() -> Tuple[bool, str]:
    """Check if current user has Docker permissions"""
    result = run_command(['docker', 'ps'])
    if result.returncode == 0:
        return True, "User has Docker permissions"
    if 'permission denied' in result.stderr.lower():
        return False, "Permission denied - user not in docker group"
    return False, result.stderr.strip()


def check_docker_socket() -> Tuple[bool, str]:
    """Check if Docker socket exists and is accessible"""
    socket_path = '/var/run/docker.sock'
    if os.path.exists(socket_path):
        if os.access(socket_path, os.R_OK | os.W_OK):
            return True, f"Docker socket is accessible: {socket_path}"
        return False, f"Docker socket exists but is not accessible: {socket_path}"
    return False, f"Docker socket not found: {socket_path}"


def check_docker_service() -> Tuple[bool, str]:
    """Check Docker service status"""
    system = platform.system().lower()
    if system == 'linux':
        # Try systemctl first
        result = run_command(['systemctl', 'is-active', 'docker'])
        if result.returncode == 0 and 'active' in result.stdout:
            return True, "Docker service is active"
        return False, "Docker service is not active"
    elif system == 'darwin':
        # macOS - check if Docker Desktop is running
        result = run_command(['pgrep', '-f', 'Docker.app'])
        if result.returncode == 0:
            return True, "Docker Desktop is running"
        return False, "Docker Desktop is not running"
    else:
        return True, "Service check not applicable for this platform"


def check_system_resources() -> Tuple[bool, str]:
    """Check if system has sufficient resources"""
    try:
        import psutil
        
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        warnings = []
        if cpu_count < 2:
            warnings.append(f"Low CPU count: {cpu_count}")
        if memory.total < 2 * 1024**3:  # 2GB
            warnings.append(f"Low memory: {memory.total / 1024**3:.1f}GB")
        if disk.percent > 90:
            warnings.append(f"Low disk space: {disk.percent}% used")
        
        if warnings:
            return False, "; ".join(warnings)
        return True, f"CPU: {cpu_count}, RAM: {memory.total / 1024**3:.1f}GB, Disk: {disk.percent}% used"
    except ImportError:
        return True, "psutil not installed - skipping resource check"


def check_network_connectivity() -> Tuple[bool, str]:
    """Check if Docker Hub is accessible"""
    result = run_command(['docker', 'search', '--limit', '1', 'alpine'])
    if result.returncode == 0:
        return True, "Docker Hub is accessible"
    return False, "Cannot reach Docker Hub"


def fix_docker_permissions(auto_fix: bool) -> bool:
    """Fix Docker permissions by adding user to docker group"""
    system = platform.system().lower()
    if system != 'linux':
        print_fix("Permission fix only applicable on Linux")
        return False
    
    username = os.getenv('USER')
    if not username:
        print_fix("Could not determine username")
        return False
    
    print_fix(f"Adding user '{username}' to docker group")
    
    if auto_fix:
        result = run_command(['sudo', 'usermod', '-aG', 'docker', username], capture=False)
        if result.returncode == 0:
            print(f"  {Colors.GREEN}✓{Colors.ENDC} User added to docker group")
            print(f"  {Colors.YELLOW}⚠{Colors.ENDC}  You need to log out and back in for changes to take effect")
            return True
        else:
            print(f"  {Colors.RED}✗{Colors.ENDC} Failed to add user to docker group")
            return False
    else:
        print(f"  Run: sudo usermod -aG docker {username}")
        print(f"  Then log out and back in")
        return False


def fix_docker_service(auto_fix: bool) -> bool:
    """Start Docker service"""
    system = platform.system().lower()
    
    if system == 'linux':
        print_fix("Starting Docker service")
        if auto_fix:
            result = run_command(['sudo', 'systemctl', 'start', 'docker'], capture=False)
            if result.returncode == 0:
                # Also enable it
                run_command(['sudo', 'systemctl', 'enable', 'docker'], capture=False)
                print(f"  {Colors.GREEN}✓{Colors.ENDC} Docker service started and enabled")
                return True
            else:
                print(f"  {Colors.RED}✗{Colors.ENDC} Failed to start Docker service")
                return False
        else:
            print("  Run: sudo systemctl start docker")
            print("  And: sudo systemctl enable docker")
            return False
    elif system == 'darwin':
        print_fix("Please start Docker Desktop application manually")
        return False
    else:
        print_fix("Please start Docker Desktop manually")
        return False


def diagnose_docker_daemon_issues() -> List[str]:
    """Diagnose why Docker daemon might not be working"""
    issues = []
    
    # Check if Docker is installed
    if not shutil.which('docker'):
        issues.append("Docker CLI is not installed")
        return issues
    
    # Check Docker service
    system = platform.system().lower()
    if system == 'linux':
        result = run_command(['systemctl', 'status', 'docker'])
        if 'could not be found' in result.stderr.lower():
            issues.append("Docker service is not installed")
        elif 'inactive' in result.stdout.lower() or 'dead' in result.stdout.lower():
            issues.append("Docker service is stopped")
        
        # Check for AppArmor/SELinux issues
        result = run_command(['journalctl', '-u', 'docker', '-n', '20', '--no-pager'])
        if 'apparmor' in result.stdout.lower():
            issues.append("AppArmor may be blocking Docker")
        if 'selinux' in result.stdout.lower():
            issues.append("SELinux may be blocking Docker")
    
    return issues


def main(argv=None):
    """Main entry point for dmm-doctor"""
    if argv is None:
        argv = sys.argv[1:]
    
    auto_fix = '--fix' in argv or '-f' in argv
    verbose = '--verbose' in argv or '-v' in argv
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}🏥 Docker Monitor Manager - System Doctor{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    
    if auto_fix:
        print(f"{Colors.YELLOW}🔧 Auto-fix mode enabled{Colors.ENDC}\n")
    
    # Track issues
    issues_found = 0
    issues_fixed = 0
    
    # Check 1: Docker Installation
    print_header("1. Docker Installation")
    status, message = check_docker_installed()
    print_check("Docker installed", status, message)
    if not status:
        issues_found += 1
        print(f"\n{Colors.YELLOW}Please install Docker first using: dmm-config{Colors.ENDC}\n")
        return 1
    
    # Check 2: Docker Service
    print_header("2. Docker Service Status")
    status, message = check_docker_service()
    print_check("Docker service", status, message)
    if not status:
        issues_found += 1
        if fix_docker_service(auto_fix):
            issues_fixed += 1
    
    # Check 3: Docker Daemon
    print_header("3. Docker Daemon")
    status, message = check_docker_running()
    print_check("Docker daemon running", status, message)
    if not status:
        issues_found += 1
        # Diagnose issues
        daemon_issues = diagnose_docker_daemon_issues()
        if daemon_issues:
            print(f"\n  {Colors.YELLOW}Diagnosed issues:{Colors.ENDC}")
            for issue in daemon_issues:
                print(f"    • {issue}")
    
    # Check 4: Docker Permissions
    print_header("4. Docker Permissions")
    status, message = check_docker_permissions()
    print_check("Docker permissions", status, message)
    if not status and 'permission denied' in message.lower():
        issues_found += 1
        if fix_docker_permissions(auto_fix):
            issues_fixed += 1
    
    # Check 5: Docker Socket
    print_header("5. Docker Socket")
    status, message = check_docker_socket()
    print_check("Docker socket", status, message)
    if not status:
        issues_found += 1
    
    # Check 6: Network Connectivity
    print_header("6. Network Connectivity")
    status, message = check_network_connectivity()
    print_check("Docker Hub access", status, message)
    if not status:
        issues_found += 1
        print(f"  {Colors.YELLOW}→{Colors.ENDC} Check your internet connection and proxy settings")
    
    # Check 7: System Resources
    print_header("7. System Resources")
    status, message = check_system_resources()
    print_check("System resources", status, message)
    if not status:
        issues_found += 1
    
    # Summary
    print_header("Summary")
    if issues_found == 0:
        print(f"{Colors.GREEN}✓ All checks passed! Your system is healthy.{Colors.ENDC}\n")
        return 0
    else:
        print(f"{Colors.YELLOW}⚠ Found {issues_found} issue(s){Colors.ENDC}")
        if auto_fix and issues_fixed > 0:
            print(f"{Colors.GREEN}✓ Fixed {issues_fixed} issue(s){Colors.ENDC}")
        
        if not auto_fix:
            print(f"\n{Colors.CYAN}Tip: Run with --fix to automatically fix issues:{Colors.ENDC}")
            print(f"  dmm-doctor --fix\n")
        else:
            remaining = issues_found - issues_fixed
            if remaining > 0:
                print(f"{Colors.YELLOW}⚠ {remaining} issue(s) require manual intervention{Colors.ENDC}\n")
        
        return 1


if __name__ == '__main__':
    sys.exit(main())
