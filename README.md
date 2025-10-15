# docker-monitor-manager 🐳📊

A small, native desktop tool for monitoring and managing Docker containers, written in Python with Tkinter.

This repository provides a GUI application and helpful CLI tools for Docker management. It exposes the following console entry points when installed:

- `docker-monitor-manager` / `dmm` - Desktop GUI application
- `dmm-config` - System configuration helper
- `dmm-doctor` - Health checker and auto-fixer
- `dmm-test` - Test environment creator
- `dmm-setup` - Post-installation setup (desktop entry & icons)
- `dmm-update` - Update to the latest version from PyPI
- `dmm-help` - Display help and documentation for all CLI tools
- `dmm-uninstall` - Complete uninstaller

---

## What it does

- Live container stats (CPU% and RAM%) shown in a native Tkinter window.
- Auto-scaling behaviour (creates lightweight clones of overloaded containers, and manages clones in a simple policy).
- Basic container management actions from the UI (stop, pause, restart, remove, etc.).
- Embedded, restricted terminal for running safe `docker ...` commands from the GUI.
- Application log view for real-time monitoring of what the app is doing.
- Comprehensive CLI tools for system configuration, health checking, and maintenance.
- Built-in help system (`dmm-help`) that provides detailed documentation for all commands.
- Auto-update functionality (`dmm-update`) to easily upgrade to the latest version.
- A conservative CLI helper (`dmm-doctor`) that can detect Docker and AppArmor issues and optionally help fix them on supported systems.

---

## Features ✨
- 📈 **Live container stats** (CPU%, RAM%)  
- ⚡ **Auto-scale** containers when resource limits are exceeded  
- ⏯️ **Manage containers**: Stop, Pause, Unpause, Restart, and Remove containers directly from the UI.
- 🎛️ **Global controls**: Apply actions to all containers at once.
- 🖥️ **Embedded Terminal**: A secure terminal for running `docker` commands.
- 📝 **Live Application Logs**: See what the monitor is doing in real-time.
- ⚙️ **Dynamic Configuration**: Adjust CPU/RAM limits and other settings without restarting the app.
- 🔄 **Auto-Update**: Update to the latest version with a single command (`dmm-update`)
- 📚 **Comprehensive Help**: Built-in help system for all CLI tools (`dmm-help`)
- 🏥 **Health Checker**: Automatic diagnosis and fixing of common Docker issues (`dmm-doctor`)
- 🧪 **Test Environment**: Easily create test containers for verification (`dmm-test`)

---

## Installation 🚀

### Option 1: Install from PyPI (if published)
```bash
pip install docker-monitor-manager
```

### Option 2: Install with pipx
```bash
sudo apt install pipx   # (or install pipx by your OS method)
pipx install docker-monitor-manager
```

### Option 3: Install from source (local)
```bash
git clone https://github.com/amir-khoshdel-louyeh/docker-monitor-manager.git
cd docker-monitor-manager
pip install .
```

**⚠️ Important: After installation, run the setup command:**
```bash
dmm-setup
```
This installs the desktop entry and icons, making the app searchable in your application menu.


### Prerequisites

- Python 3.8+
- Docker Engine (installed and running)
- On Linux, to use Docker without sudo, add your user to the `docker` group:

```bash
sudo usermod -aG docker $USER
# then log out and back in, or run:
newgrp docker
```

Verify membership (after restarting your system or logging out/in):

```bash
getent group docker
```



If you see permission denied errors when accessing Docker, make sure the Docker daemon is running and your user has permission (see Troubleshooting below).

---

## Usage

After installation, first run the setup:

```bash
dmm-setup
```

Then you can run the GUI:

```bash
docker-monitor-manager
# or
dmm
```

Or search for "Docker Monitor Manager" in your application menu!

### CLI Tools

#### 📚 Get help and documentation:

```bash
dmm-help           # show all available commands
dmm-help <command> # show detailed help for a specific command
dmm-help doctor    # example: get help about dmm-doctor
```

#### 🔄 Update to the latest version:

```bash
dmm-update         # update from PyPI
dmm-update --force # force reinstall
```

#### 🏥 Check system health and auto-fix issues:

```bash
dmm-doctor         # diagnose issues
dmm-doctor --fix   # diagnose and auto-fix
```

#### ⚙️ Configure Docker installation:

```bash
dmm-config         # interactive (prompts before making changes)
dmm-config --yes   # non-interactive (accept prompts)
```

#### 🧪 Create test environment:

```bash
dmm-test           # create test containers
dmm-test --status  # check status
dmm-test --cleanup # remove test containers
```

#### 🗑️ Uninstall completely:

```bash
dmm-uninstall      # remove application, icons, and desktop entries

---

## All Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `dmm` / `docker-monitor-manager` | Launch the GUI application | `dmm` |
| `dmm-help` | Show help for all commands | `dmm-help` |
| `dmm-help <command>` | Show detailed help for a command | `dmm-help doctor` |
| `dmm-update` | Update to the latest version | `dmm-update` |
| `dmm-setup` | Run post-installation setup | `dmm-setup` |
| `dmm-doctor` | Check system health | `dmm-doctor --fix` |
| `dmm-config` | Configure Docker installation | `dmm-config` |
| `dmm-test` | Create test containers | `dmm-test` |
| `dmm-uninstall` | Uninstall the application | `dmm-uninstall` |

**Quick Command Reference:**
```bash
dmm-help           # Get help anytime
dmm-update         # Stay up to date
dmm-doctor --fix   # Fix any issues
dmm                # Run the application
```

---

## Quick Start

First-time setup:

```bash
# 1. Install the package
pip install docker-monitor-manager

# 2. Run post-installation setup
dmm-setup

# 3. Check system health
dmm-doctor --fix

# 4. (Optional) Create test environment
dmm-test

# 5. Launch the application
dmm
```

To get help anytime:
```bash
dmm-help           # show all commands
dmm-help <command> # detailed help for a specific command
```

---

## CLI Tools Overview

### 📚 `dmm-help`
Display comprehensive help and documentation for all CLI tools.

**Features**:
- Shows overview of all available commands
- Provides detailed help for specific commands
- Includes usage examples and explanations
- Beautiful colored terminal output

**Usage**:
```bash
dmm-help           # show main help screen
dmm-help doctor    # detailed help for dmm-doctor
dmm-help update    # detailed help for dmm-update
dmm-help config    # detailed help for dmm-config
```

### 🔄 `dmm-update`
Update Docker Monitor Manager to the latest version from PyPI.

**Features**:
- Checks current installed version
- Downloads and installs the latest version
- Automatically runs post-installation setup
- Preserves your configuration and settings
- Supports force reinstall option

**Usage**:
```bash
dmm-update         # update to latest version
dmm-update --force # force reinstall even if already latest
```

### 🏥 `dmm-doctor`
Health checker and auto-fixer for common Docker issues.

**Checks**:
- ✓ Docker installation
- ✓ Docker service status  
- ✓ Docker daemon connectivity
- ✓ User permissions
- ✓ Docker socket accessibility
- ✓ Network connectivity
- ✓ System resources

**Usage**:
```bash
dmm-doctor         # diagnose only
dmm-doctor --fix   # auto-fix issues
```

### 🧪 `dmm-test`
Create test Docker containers for verifying the application works correctly.

**Creates**:
- Normal containers (nginx, redis, postgres)
- CPU stress containers (for testing resource monitoring)
- Memory stress containers (for testing memory limits)
- Cloneable containers (for testing clone functionality)
- Stopped containers (for testing restart)

**Usage**:
```bash
dmm-test           # create all test containers
dmm-test --cpu     # create only CPU stress
dmm-test --memory  # create only memory stress
dmm-test --status  # show container status
dmm-test --cleanup # remove all test containers
```

### ⚙️ `dmm-config`
Interactive system configuration helper.

**Features**:
- Detects and installs Docker
- Configures AppArmor/SELinux
- Sets up proper permissions

**Usage**:
```bash
dmm-config         # interactive mode
dmm-config --yes   # auto-accept all prompts
```

### 🗑️ `dmm-uninstall`
Complete uninstaller that removes all application files and settings.

**Removes**:
- Python package (automatically detects pip, pip3, or pipx installation)
- Desktop entry (.desktop file)
- All icons (Linux/Windows/macOS)
- Configuration files (optional)

**Supports**:
- ✅ pip install
- ✅ pip3 install  
- ✅ pipx install
- ✅ Development mode (pip install -e .)
- ✅ User install (pip install --user)

**Usage**:
```bash
dmm-uninstall      # interactive uninstall (auto-detects installation method)

---

## dmm-config — quick reference

`dmm-config` is a small CLI tool included in the package. It performs checks and (optionally) fixes common issues required for this app to talk to Docker.

What it does
- Detects whether `docker` is available on PATH (`docker --version`).
- On Linux it can attempt to install Docker via the distro package manager (or suggest the official install script) and can offer to install AppArmor utilities when appropriate.
- If `/etc/apparmor.d/docker` exists, it can offer to switch the profile to `complain` or `disable` using `aa-complain` / `aa-disable`.

Security & behavior
- The helper is conservative — it asks before making system changes. Use `--yes` only when you trust the environment and want automatic changes.

Manual AppArmor commands (Debian/Ubuntu example)
```bash
sudo apt-get update
sudo apt-get install apparmor-utils
sudo aa-status
sudo aa-complain /etc/apparmor.d/docker
sudo aa-disable /etc/apparmor.d/docker
```

---

## Troubleshooting (common)

**Need help?** Run `dmm-help` to see all available commands and their usage.

- **"permission denied" when accessing Docker:**
	- Run `dmm-doctor --fix` to automatically diagnose and fix the issue.
	- Or manually: Ensure the Docker daemon is running: `sudo systemctl start docker` (or use your distro's service manager).
	- Add your user to the `docker` group and re-login: `sudo usermod -aG docker $USER` then logout/login or `newgrp docker`.
	- If AppArmor is interfering, use `dmm-config` to inspect and optionally change the Docker AppArmor profile.

- **Application not working correctly:**
	- Run `dmm-doctor` to check for common issues.
	- Run `dmm-test` to create test containers and verify functionality.

- **Want to update to the latest version:**
	- Simply run `dmm-update` to download and install the latest version from PyPI.

---

## Developer / Maintainer notes

- Quick syntax check (compile-only):
```bash
python3 -m py_compile docker_monitor/*.py
```

- Quick import test:
```bash
python3 -c "import docker_monitor.main as m; print('OK')"
```

- Build distributions (wheel & sdist):
```bash
pip install build
python -m build
```

Source layout and important files
- `docker_monitor/__init__.py` — package metadata (version, author).
- `docker_monitor/main.py` — main GUI application and console entry point.
- `docker_monitor/cli/` — CLI tools directory:
  - `config.py` — `dmm-config` system configuration helper.
  - `doctor.py` — `dmm-doctor` health checker and auto-fixer.
  - `test.py` — `dmm-test` test environment creator.
  - `setup.py` — `dmm-setup` post-installation setup.
  - `update.py` — `dmm-update` auto-updater.
  - `help.py` — `dmm-help` help and documentation system.
  - `uninstall.py` — `dmm-uninstall` complete uninstaller.
- `docker_monitor/gui/` — GUI components (app, managers, widgets).
- `docker_monitor/utils/` — Utility modules (Docker utils, buffer handler).
- `requirements.txt` / `pyproject.toml` — declare runtime dependencies (notably `docker` and `Pillow`).

---

## Packaging & platform notes

- Windows: the GUI attempts to use generated `.ico` if available (requires Pillow to generate icons).
- macOS: packaging as a `.app` (py2app) is recommended for a native experience and to generate `.icns` correctly.
- Linux: Tkinter `PhotoImage` PNGs usually work for in-window icons.

---

## Security notes

- The embedded terminal widget only allows commands that start with `docker` — arbitrary shell commands are rejected by design. the only exeption is `clear` command. 
- `dmm-config` may run package-manager commands with `sudo` when requested by the user. It is intentionally conservative and prompts before making changes.

---

