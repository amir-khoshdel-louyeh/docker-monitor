#!/usr/bin/env python3
"""
dmm-help: Display help and documentation for Docker Monitor Manager CLI tools

This tool provides comprehensive help and usage information for all dmm commands.
"""
from __future__ import annotations

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
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.ENDC}")


def print_subheader(text: str):
    """Print a subsection header"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}{text}{Colors.ENDC}")
    print(f"{Colors.YELLOW}{'-'*70}{Colors.ENDC}")


def print_command(name: str, description: str):
    """Print a command with its description"""
    print(f"  {Colors.GREEN}{Colors.BOLD}{name:<25}{Colors.ENDC} {Colors.CYAN}{description}{Colors.ENDC}")


def print_example(command: str, description: str = ""):
    """Print an example command"""
    print(f"  {Colors.BOLD}${Colors.ENDC} {Colors.CYAN}{command}{Colors.ENDC}")
    if description:
        print(f"    {Colors.YELLOW}→ {description}{Colors.ENDC}")


def print_info(text: str):
    """Print an info message"""
    print(f"{Colors.CYAN}{text}{Colors.ENDC}")


def show_main_help():
    """Show the main help screen"""
    print_header("Docker Monitor Manager - CLI Tools")
    
    print(f"\n{Colors.BOLD}Docker Monitor Manager{Colors.ENDC} is a powerful desktop tool for")
    print("monitoring and managing Docker containers with an intuitive GUI.")
    
    print_subheader("🚀 Main Commands")
    print_command("dmm", "Launch Docker Monitor Manager GUI application")
    print_command("docker-monitor-manager", "Alternative command to launch the GUI")
    
    print_subheader("🔧 Management Commands")
    print_command("dmm-config", "Configure application settings and preferences")
    print_command("dmm-setup", "Run post-installation setup (desktop entry & icons)")
    print_command("dmm-update", "Update to the latest version from PyPI")
    print_command("dmm-uninstall", "Uninstall Docker Monitor Manager from system")
    
    print_subheader("🩺 Diagnostic Commands")
    print_command("dmm-doctor", "Check system health and auto-fix common issues")
    print_command("dmm-test", "Run application tests and verify installation")
    
    print_subheader("📚 Information Commands")
    print_command("dmm-help", "Show this help message")
    print_command("dmm-help <command>", "Show detailed help for a specific command")
    
    print_subheader("💡 Quick Start Examples")
    print_example("dmm", "Start the application")
    print_example("dmm-doctor", "Check if everything is working correctly")
    print_example("dmm-config", "Configure application settings")
    print_example("dmm-update", "Update to the latest version")
    print_example("dmm-help doctor", "Get detailed help about dmm-doctor")
    
    print_subheader("📖 Getting More Help")
    print(f"  • Run {Colors.GREEN}dmm-help <command>{Colors.ENDC} for detailed information")
    print(f"  • Visit: {Colors.CYAN}https://github.com/amir-khoshdel-louyeh/docker-monitor-manager{Colors.ENDC}")
    print(f"  • Report issues: {Colors.CYAN}https://github.com/amir-khoshdel-louyeh/docker-monitor-manager/issues{Colors.ENDC}")
    
    print("\n")


def show_command_help(command: str):
    """Show detailed help for a specific command"""
    
    command = command.lower().replace('dmm-', '')
    
    help_content = {
        'dmm': {
            'title': 'dmm / docker-monitor-manager',
            'description': 'Launch the Docker Monitor Manager GUI application.',
            'usage': 'dmm',
            'details': [
                'This is the main command to start the graphical user interface.',
                'The application provides a comprehensive dashboard for:',
                '  • Monitoring running containers and their stats (CPU, memory, network)',
                '  • Managing containers (start, stop, restart, remove)',
                '  • Managing Docker images, volumes, and networks',
                '  • Viewing container logs and executing commands',
                '  • System-wide Docker information and resource usage',
            ],
            'examples': [
                ('dmm', 'Start the application'),
                ('docker-monitor-manager', 'Alternative way to start'),
            ]
        },
        'config': {
            'title': 'dmm-config',
            'description': 'Configure Docker Monitor Manager settings and preferences.',
            'usage': 'dmm-config [options]',
            'details': [
                'Manage application configuration including:',
                '  • Docker connection settings',
                '  • Refresh intervals and timeouts',
                '  • Theme and appearance preferences',
                '  • Notification settings',
                '  • Default behaviors',
            ],
            'examples': [
                ('dmm-config', 'Open configuration manager'),
                ('dmm-config --reset', 'Reset to default settings'),
            ]
        },
        'doctor': {
            'title': 'dmm-doctor',
            'description': 'System health checker and auto-fixer for common Docker issues.',
            'usage': 'dmm-doctor [options]',
            'details': [
                'Diagnoses and fixes common problems:',
                '  • Docker installation and service status',
                '  • Docker daemon connectivity',
                '  • User permissions (docker group membership)',
                '  • AppArmor/SELinux conflicts',
                '  • Network connectivity issues',
                '  • Container runtime problems',
                '  • System resource availability',
                '',
                'The doctor can automatically fix many issues it finds.',
            ],
            'examples': [
                ('dmm-doctor', 'Run full system diagnostic'),
                ('dmm-doctor --fix', 'Auto-fix detected issues'),
            ]
        },
        'setup': {
            'title': 'dmm-setup',
            'description': 'Run post-installation setup tasks.',
            'usage': 'dmm-setup',
            'details': [
                'Performs post-installation configuration:',
                '  • Installs desktop entry (.desktop file)',
                '  • Installs application icons',
                '  • Sets up application menu integration',
                '  • Configures system paths',
                '',
                'This is automatically run during installation, but you can',
                'run it manually if needed.',
            ],
            'examples': [
                ('dmm-setup', 'Run post-installation setup'),
            ]
        },
        'update': {
            'title': 'dmm-update',
            'description': 'Update Docker Monitor Manager to the latest version.',
            'usage': 'dmm-update [options]',
            'details': [
                'Updates the application to the latest version from PyPI:',
                '  • Checks current installed version',
                '  • Downloads and installs the latest version',
                '  • Runs post-installation setup automatically',
                '  • Preserves your configuration and settings',
                '',
                'Options:',
                '  --force, -f    Force reinstall even if already latest version',
            ],
            'examples': [
                ('dmm-update', 'Update to latest version'),
                ('dmm-update --force', 'Force reinstall'),
            ]
        },
        'uninstall': {
            'title': 'dmm-uninstall',
            'description': 'Uninstall Docker Monitor Manager from the system.',
            'usage': 'dmm-uninstall [options]',
            'details': [
                'Removes the application from your system:',
                '  • Removes desktop entry and icons',
                '  • Cleans up configuration files',
                '  • Uninstalls the Python package',
                '',
                'Your Docker containers and data are not affected.',
            ],
            'examples': [
                ('dmm-uninstall', 'Uninstall the application'),
            ]
        },
        'test': {
            'title': 'dmm-test',
            'description': 'Run application tests and verify installation.',
            'usage': 'dmm-test [options]',
            'details': [
                'Verifies the installation and runs tests:',
                '  • Checks if all dependencies are installed',
                '  • Tests Docker connectivity',
                '  • Verifies application components',
                '  • Runs basic functionality tests',
            ],
            'examples': [
                ('dmm-test', 'Run all tests'),
                ('dmm-test --verbose', 'Run with detailed output'),
            ]
        },
        'help': {
            'title': 'dmm-help',
            'description': 'Display help and documentation for DMM CLI tools.',
            'usage': 'dmm-help [command]',
            'details': [
                'Shows help information:',
                '  • Without arguments: shows overview of all commands',
                '  • With command name: shows detailed help for that command',
            ],
            'examples': [
                ('dmm-help', 'Show main help'),
                ('dmm-help doctor', 'Show help for dmm-doctor'),
                ('dmm-help update', 'Show help for dmm-update'),
            ]
        },
    }
    
    if command not in help_content:
        print(f"\n{Colors.RED}Unknown command: {command}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Run 'dmm-help' to see all available commands.{Colors.ENDC}\n")
        return
    
    content = help_content[command]
    
    print_header(content['title'])
    
    print(f"\n{Colors.BOLD}Description:{Colors.ENDC}")
    print(f"  {content['description']}")
    
    print(f"\n{Colors.BOLD}Usage:{Colors.ENDC}")
    print(f"  {Colors.GREEN}{content['usage']}{Colors.ENDC}")
    
    if content.get('details'):
        print(f"\n{Colors.BOLD}Details:{Colors.ENDC}")
        for line in content['details']:
            if line:
                print(f"  {line}")
            else:
                print()
    
    if content.get('examples'):
        print(f"\n{Colors.BOLD}Examples:{Colors.ENDC}")
        for cmd, desc in content['examples']:
            print_example(cmd, desc)
    
    print("\n")


def main():
    """Main entry point for the help command"""
    
    # Get command argument if provided
    command = None
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command in ['-h', '--help']:
            command = None
    
    if command:
        show_command_help(command)
    else:
        show_main_help()


if __name__ == "__main__":
    main()
