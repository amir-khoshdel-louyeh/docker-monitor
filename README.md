# docker-monitor-manager 🐳📊

A small, native desktop tool for monitoring and managing Docker containers, written in Python with Tkinter.

This repository provides a GUI application and helpful CLI tools for Docker management. It exposes the following console entry points when installed:

- `docker-monitor-manager` / `dmm` - Desktop GUI application
- `dmm-config` - System configuration helper
- `dmm-doctor` - Health checker and auto-fixer
- `dmm-test` - Test environment creator

---

## What it does

- Live container stats (CPU% and RAM%) shown in a native Tkinter window.
- Auto-scaling behaviour (creates lightweight clones of overloaded containers, and manages clones in a simple policy).
- Basic container management actions from the UI (stop, pause, restart, remove, etc.).
- Embedded, restricted terminal for running safe `docker ...` commands from the GUI.
- Application log view for real-time monitoring of what the app is doing.
- A conservative CLI helper (`dmm-config`) that can detect Docker and AppArmor issues and optionally help fix them on supported systems.

---

## Features ✨
- 📈 **Live container stats** (CPU%, RAM%)  
- ⚡ **Auto-scale** containers when resource limits are exceeded  
- ⏯️ **Manage containers**: Stop, Pause, Unpause, Restart, and Remove containers directly from the UI.
- 🎛️ **Global controls**: Apply actions to all containers at once.
- 🖥️ **Embedded Terminal**: A secure terminal for running `docker` commands.
- 📝 **Live Application Logs**: See what the monitor is doing in real-time.
- ⚙️ **Dynamic Configuration**: Adjust CPU/RAM limits and other settings without restarting the app.

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

After installation you can run the GUI:

```bash
docker-monitor-manager
# or
dmm
```

### CLI Tools

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

For detailed CLI documentation, see [CLI Tools Guide](docs/CLI_TOOLS.md) or [راهنمای ابزارهای خط فرمان](docs/CLI_TOOLS_FA.md).

---

## Quick Start

First-time setup:

```bash
# 1. Configure Docker
dmm-config

# 2. Check system health
dmm-doctor --fix

# 3. Create test environment
dmm-test

# 4. Launch the application
dmm
```

---

## CLI Tools Overview

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

For detailed documentation, see [CLI Tools Guide](docs/CLI_TOOLS.md).

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

- "permission denied" when accessing Docker:
	- Ensure the Docker daemon is running: `sudo systemctl start docker` (or use your distro's service manager).
	- Add your user to the `docker` group and re-login: `sudo usermod -aG docker $USER` then logout/login or `newgrp docker`.
	- If AppArmor is interfering, use `dmm-config` to inspect and optionally change the Docker AppArmor profile.

- GUI icon missing or low quality:
	- Make sure Pillow is installed: `pip install Pillow`
	- Replace `docker_monitor/logo.png` with a high-resolution square PNG (512×512 or 1024×1024) and restart.

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
- `docker_monitor/config_cli.py` — `dmm-config` system helper.
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

