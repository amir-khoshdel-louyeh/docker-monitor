#!/usr/bin/env python3
"""Small CLI to help users configure their system for docker-monitor-manager.

Provides an interactive command `dmm-config` that can:
- Check whether Docker is installed and (optionally) attempt to install it.
- On Linux/Ubuntu, ensure AppArmor utilities are available (apparmor-utils)
  and optionally switch the Docker AppArmor profile to complain/disabled to
  avoid permission denied issues.

The script is conservative: it won't perform network installs unless the
user confirms or uses --yes. It tries to handle macOS, Windows and several
Linux distros.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from typing import List


def run(cmd: List[str], capture: bool = True) -> subprocess.CompletedProcess:
    try:
        if capture:
            return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        else:
            return subprocess.run(cmd, check=False)
    except FileNotFoundError:
        # Command not found
        raise


def prompt_yes(question: str, auto_yes: bool) -> bool:
    if auto_yes:
        print(question + ' [auto-yes]')
        return True
    try:
        resp = input(question + ' [y/N]: ').strip().lower()
        return resp in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        return False


def is_command_available(name: str) -> bool:
    return shutil.which(name) is not None


def check_docker() -> bool:
    try:
        res = run(['docker', '--version'])
        if res.returncode == 0:
            print('Docker is installed:', res.stdout.strip())
            return True
    except FileNotFoundError:
        pass
    print('Docker is not installed or not available on PATH.')
    return False


def install_docker_linux(auto_yes: bool) -> bool:
    # Try to detect package manager
    os_release = {}
    try:
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if '=' in line:
                    k, v = line.rstrip().split('=', 1)
                    os_release[k] = v.strip('"')
    except FileNotFoundError:
        pass

    id_like = os_release.get('ID', '').lower()
    pretty = os_release.get('PRETTY_NAME', id_like)

    print(f'Detected Linux distribution: {pretty}')

    # Prefer distro packages for Debian/Ubuntu
    if 'ubuntu' in id_like or 'debian' in id_like:
        print('Attempting to install Docker via apt (docker.io).')
        if not prompt_yes('Run: sudo apt-get update && sudo apt-get install -y docker.io ?', auto_yes):
            print('Skipping apt-based install. You can install Docker manually or use the official script.')
            return False
        cmds = [
            ['sudo', 'apt-get', 'update'],
            ['sudo', 'apt-get', 'install', '-y', 'docker.io'],
        ]
    else:
        # try common package managers: dnf, yum, pacman
        if is_command_available('dnf'):
            print('Attempting to install Docker via dnf (dnf install -y docker).')
            cmds = [['sudo', 'dnf', 'install', '-y', 'docker']]
        elif is_command_available('yum'):
            print('Attempting to install Docker via yum (yum install -y docker).')
            cmds = [['sudo', 'yum', 'install', '-y', 'docker']]
        elif is_command_available('pacman'):
            print('Attempting to install Docker via pacman (pacman -S --noconfirm docker).')
            cmds = [['sudo', 'pacman', '-S', '--noconfirm', 'docker']]
        else:
            print('Could not find a supported package manager. You can use the official install script from get.docker.com.')
            if not prompt_yes('Run the official Docker install script (curl -fsSL https://get.docker.com | sudo sh)?', auto_yes):
                return False
            cmds = [['sh', '-c', 'curl -fsSL https://get.docker.com | sudo sh']]

    for c in cmds:
        print('Running:', ' '.join(c))
        proc = run(c, capture=False)
        if proc.returncode != 0:
            print('Command failed:', ' '.join(c))
            return False

    print('Docker install finished. Please log out/log in or restart the docker service if necessary.')
    return check_docker()


def install_docker_macos(auto_yes: bool) -> bool:
    # Prefer Homebrew if available
    if is_command_available('brew'):
        print('Homebrew detected. Installing Docker Desktop via brew cask.')
        if not prompt_yes('Run: brew install --cask docker ?', auto_yes):
            print('Skipping brew cask install. Please install Docker Desktop from https://www.docker.com/get-started')
            return False
        proc = run(['brew', 'install', '--cask', 'docker'], capture=False)
        if proc.returncode != 0:
            print('brew cask install failed.')
            return False
        return check_docker()
    else:
        print('Homebrew not found. Please install Docker Desktop from https://www.docker.com/get-started')
        return False


def install_docker_windows(auto_yes: bool) -> bool:
    # Try winget or choco
    if is_command_available('winget'):
        print('Attempting to install Docker Desktop via winget.')
        if not prompt_yes('Run: winget install --id Docker.DockerDesktop -e ?', auto_yes):
            print('Skipping winget install. Please install Docker Desktop from https://www.docker.com/get-started')
            return False
        proc = run(['winget', 'install', '--id', 'Docker.DockerDesktop', '-e'], capture=False)
        return proc.returncode == 0 and check_docker()
    if is_command_available('choco'):
        print('Attempting to install Docker Desktop via choco.')
        if not prompt_yes('Run: choco install docker-desktop -y ?', auto_yes):
            print('Skipping choco install. Please install Docker Desktop from https://www.docker.com/get-started')
            return False
        proc = run(['choco', 'install', 'docker-desktop', '-y'], capture=False)
        return proc.returncode == 0 and check_docker()

    print('Please install Docker Desktop for Windows from https://www.docker.com/get-started')
    return False


def ensure_apparmor_utils_linux(auto_yes: bool) -> None:
    # Only meaningful on Linux
    if not is_command_available('aa-status'):
        print('AppArmor utilities (aa-status/aa-complain/aa-disable) not found.')
        # Check for Ubuntu/Debian
        distro = ''
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('ID='):
                        distro = line.split('=', 1)[1].strip().strip('"').lower()
        except Exception:
            pass

        if distro in ('ubuntu', 'debian'):
            print('On Ubuntu/Debian these tools are provided by package apparmor-utils.')
            if prompt_yes('Run: sudo apt-get update && sudo apt-get install -y apparmor-utils ?', auto_yes):
                rc = run(['sudo', 'apt-get', 'update'], capture=False)
                if rc.returncode == 0:
                    rc2 = run(['sudo', 'apt-get', 'install', '-y', 'apparmor-utils'], capture=False)
                    if rc2.returncode == 0:
                        print('apparmor-utils installed.')
                    else:
                        print('Failed to install apparmor-utils.')
                else:
                    print('apt-get update failed.')
        else:
            print('Could not detect Ubuntu/Debian. Please install your distribution equivalent of apparmor-utils (aa-complain/aa-disable).')
    else:
        print('AppArmor utilities present.')

    # If Docker AppArmor profile exists, offer to switch it
    profile_path = '/etc/apparmor.d/docker'
    if os.path.exists(profile_path) and is_command_available('aa-complain'):
        print(f'Found AppArmor profile at {profile_path}')
        if prompt_yes('Run: sudo aa-complain /etc/apparmor.d/docker (switch Docker profile to complain)?', auto_yes):
            run(['sudo', 'aa-complain', profile_path], capture=False)
        if prompt_yes('Run: sudo aa-disable /etc/apparmor.d/docker (disable Docker AppArmor profile)?', auto_yes):
            run(['sudo', 'aa-disable', profile_path], capture=False)
    else:
        if not os.path.exists(profile_path):
            print('No AppArmor profile for Docker found at /etc/apparmor.d/docker. Skipping profile changes.')


def main(argv=None):
    """Entry point for dmm-config."""
    if argv is None:
        argv = sys.argv[1:]

    auto_yes = False
    if '--yes' in argv or '-y' in argv:
        auto_yes = True

    print('dmm-config: docker-monitor-manager system configuration helper')
    system = platform.system().lower()
    print('Detected platform:', system)

    docker_ok = check_docker()
    if not docker_ok:
        if system == 'linux':
            installed = install_docker_linux(auto_yes)
            if not installed:
                print('\nDocker was not installed automatically. Please install Docker manually following https://docs.docker.com/get-docker/')
        elif system == 'darwin':
            install_docker_macos(auto_yes)
        elif system in ('windows', 'msys'):
            install_docker_windows(auto_yes)
        else:
            print('Unsupported platform for automatic Docker installation. Please install Docker manually.')

    # AppArmor is only relevant on Linux
    if system == 'linux':
        ensure_apparmor_utils_linux(auto_yes)

    print('\nConfiguration finished. If you installed system packages, a reboot or relogin may be required.')


if __name__ == '__main__':
    main()
