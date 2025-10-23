# Docker Monitor Manager — Project Report

## General information

Repository: docker-monitor-manager

Purpose: Docker Monitor Manager is a small native desktop application and set of CLI utilities for monitoring and managing Docker containers. It provides a Tkinter-based GUI for live container statistics, basic management actions (stop/pause/restart/remove), an embedded restricted terminal for running docker commands, auto-scaling behavior (lightweight clones for overloaded containers), logging, and a suite of CLI helpers for system configuration, health checks, test environments, installation/setup, updates and uninstallation.

Language & platform: Python (3.8+). The GUI uses Tkinter. The project targets Linux, macOS and Windows with platform-specific packaging notes included in the repository.

Key runtime dependencies: docker (Python SDK), Pillow (optional for icon generation). See `requirements.txt` and `pyproject.toml` for full dependency pins.

## Project structure and file concepts

Top-level files
- `README.md` — User-facing documentation, usage examples, and command reference (summarized in this report).
- `setup.py`, `pyproject.toml`, `requirements.txt` — Packaging and dependency metadata.
- `report.md` — This report (project overview and usage summary).

Main package: `docker_monitor/`
- `__init__.py` — Package metadata (version, author).
- `main.py` — Application entry point for the GUI; also used for the console entry point when installed (`docker-monitor-manager` / `dmm`).

CLI tools: `docker_monitor/cli/`
- `config.py` — `dmm-config` helper to detect / configure Docker and optional AppArmor/SELinux adjustments.
- `doctor.py` — `dmm-doctor` health checker and conservative auto-fixer for common Docker problems.
- `help.py` — `dmm-help` — displays documentation and usage for the CLI tools.
- `setup.py` — `dmm-setup` — post-installation setup (desktop entry and icons).
- `test.py` — `dmm-test` — test environment creator (creates containers used to verify monitoring).
- `update.py` — `dmm-update` — auto-update helper that pulls latest from PyPI and runs setup.
- `uninstall.py` — `dmm-uninstall` — complete uninstaller that removes installed files and desktop entries.

GUI: `docker_monitor/gui/`
- `docker_monitor_app.py` — The Tkinter application bootstrap and main window.
- `managers/` — A collection of managers handling different responsibilities in the UI:
	- `container_manager.py` — Listing containers, actions (stop, pause, restart, remove), clone management, and live stats.
	- `image_manager.py`, `network_manager.py`, `volume_manager.py`, `system_manager.py`, `prune_manager.py` — Supporting management screens and actions.
	- `info_display_manager.py` — Manages the information panels and logs.
- `widgets/` — Reusable UI widgets used in the app (embedded terminal, tooltips, common UI components).

Utilities: `docker_monitor/utils/`
- `docker_utils.py` — Thin wrappers around the Docker Python SDK used by the GUI and CLI tools.
- `buffer_handler.py` — Utilities for handling streaming logs and buffers used in the app.

Setup tools: `setup_tools/`
- Scripts and helper files for packaging, desktop entries, icons and post-install actions.

Tests: `tests/` — Test utilities and test cases (if present). These provide basic compile/import checks and test container lifecycle tests via `dmm-test`.

Other supporting files
- `MANIFEST.in`, `LICENSE`, `README.md` — Packaging and documentation artifacts for distribution.

## Project structure

This section summarizes the repository layout, where to find key functionality, and how components interact at a high level. The layout follows a conventional Python package structure with additional helper scripts for packaging and desktop integration.

- Top-level files
	- `README.md`, `report.md`, `LICENSE`, `MANIFEST.in`, `pyproject.toml`, `setup.py`, `requirements.txt` — documentation and packaging metadata. Use these for installation, release builds and developer guidance.

- Main package: `docker_monitor/`
	- `__init__.py` — package metadata and exported version information.
	- `main.py` — application entry point used by both the GUI launcher and the console entry point. This file initializes logging, config, and the main application object.

- CLI helpers: `docker_monitor/cli/`
	- Each module (`config.py`, `doctor.py`, `help.py`, `setup.py`, `test.py`, `update.py`, `uninstall.py`) implements a focused command-line utility. These are wired to console entry points (installed as `dmm-*` programs) and are lightweight, scriptable helpers that reuse shared utilities.

- GUI: `docker_monitor/gui/`
	- `docker_monitor_app.py` — bootstrap for the Tkinter UI; builds the main window and wires the managers and widgets together.
	- `managers/` — controller-style modules that encapsulate discrete responsibilities (container listing and actions, image/network/volume screens, system info, pruning, and info/log display). Managers coordinate the UI and call into the utility layer to perform work.
	- `widgets/` — reusable UI components (embedded terminal, copy-tooltips, shared UI controls) used across the GUI screens.

- Utilities: `docker_monitor/utils/`
	- `docker_utils.py` — common, thin wrappers around the Docker Python SDK used by both the GUI and CLI tools. This module centralizes Docker API calls, error handling and small adapters that make the rest of the code easier to test.
	- `buffer_handler.py` — streaming and buffer utilities for log capture and terminal I/O.

- Packaging / Helpers: `setup_tools/`
	- Contains icon creation scripts, `.desktop` template files and a `post_install.py` helper used by `dmm-setup` to integrate the app into desktop environments. These are not part of the runtime package but are used during packaging and post-install steps.

- Tests: `tests/`
	- Unit or integration helpers and test cases (where present). The `dmm-test` helper creates transient containers used by the test suite and by developers to validate monitoring features manually.

- Build artifacts: `build/` and `docker_monitor_manager.egg-info/`
	- Generated by packaging tools. Not committed for source edits; these are useful to inspect for release metadata when building locally.

How components interact (concise):

- The GUI (`docker_monitor_app.py`) composes managers and widgets. Managers call into `docker_utils.py` to query container lists, fetch stats and execute Docker operations. `buffer_handler.py` is used when streaming logs or piping command output into the embedded terminal widget.
- CLI helpers reuse `docker_utils.py` and shared helpers so the same logic is available to headless users and automated scripts. This avoids duplication between the GUI and CLI.
- `setup_tools/` is only used during packaging and the `dmm-setup` step; its scripts produce icons and desktop entries so the GUI can be launched from the desktop environment.

Where to make common changes

- To change container metrics or sampling frequency: edit the container manager implementation in `docker_monitor/gui/managers/container_manager.py`.
- To alter cloning/auto-scaling policy: find the scaling logic in the container manager and the Docker helper functions in `docker_monitor/utils/docker_utils.py` that create/manage clones.
- To add or modify CLI behavior: edit the corresponding module in `docker_monitor/cli/` and update entry point mappings in `setup.py` or `pyproject.toml`.

This `Project structure` section is intended as a quick orientation for developers and maintainers. For code-level navigation, search for names like `container_manager`, `docker_utils` and `docker_monitor_app` which are central integration points.

## What this project does (summary)

This project provides both a graphical desktop application and a set of command-line utilities for monitoring and managing Docker resources with a focus on simplicity and safety. Key capabilities include:

- Live container monitoring: The GUI displays per-container resource metrics such as CPU percentage, memory usage, and basic I/O statistics. Metrics are updated at a short interval to give the user near-real-time visibility into container behavior without requiring external monitoring stacks.

- Lightweight auto-scaling: When a container exceeds configured resource thresholds, the application can automatically create lightweight clones of that container to share load. Clone lifecycle is managed by a simple policy (scale-up when overloaded, scale-down when underutilized) to avoid runaway resource consumption. Cloning is intended for short-lived relief and testing, not as a production replacement for orchestrators.

- In-app container management: From the UI users can perform common actions such as stop, pause, unpause, restart and remove. These actions are performed through the Docker Python SDK and are presented with confirmation dialogs to reduce accidental destructive operations.

- Restricted embedded terminal: A terminal widget embedded in the GUI accepts only a limited set of safe commands (those that begin with `docker` and the `clear` command). This minimizes the risk of arbitrary command execution while enabling power users to run container commands from within the app.

- Live application logs: The app surfaces its internal logs and recent Docker events in an integrated log view. This helps with troubleshooting and understanding recent actions (for example, scale events or failed API calls).

- CLI helper utilities: A suite of small command-line programs (prefixed with `dmm-`) support installation/post-install setup, health checks, automated fixes for common issues, test environment creation (for validating monitoring features), updates, and uninstallation. These tools let advanced users script and automate common maintenance tasks.

## How to install

The project supports several common installation methods so you can choose between a system-wide library install, an isolated CLI install, or a developer/source installation. All methods have the same runtime prerequisites (Python 3.8+, and a running Docker Engine).

1) Install from PyPI (stable release):
	- This is the simplest method for end users. It installs the package and exposes the CLI entry points.
	- Example: `pip install docker-monitor-manager`

2) Install with pipx (recommended for isolated CLI installs):
	- `pipx` creates a per-application virtual environment and puts the CLI into your PATH without touching your system Python packages.
	- Example: `pipx install docker-monitor-manager`

3) Install from source (developer / local install):
	- Useful if you want to modify the code or use the latest master branch.
	- Example:
	  - `git clone <repo>`
	  - `cd docker-monitor-manager`
	  - `pip install .`

Post-install step (desktop integration):
- Run `dmm-setup` after installation to create the desktop entry and install icons so the GUI appears in your desktop environment's application menu. On Linux this creates a `.desktop` file in the appropriate user applications directory.

Runtime prerequisites and notes:
- Python 3.8 or newer.
- Docker Engine must be installed and running (daemon active).
- On Linux, to allow non-root Docker access: `sudo usermod -aG docker $USER` and then re-login or run `newgrp docker`.
- The application depends on the Python `docker` package (Docker SDK) and optionally `Pillow` for icon manipulation. Exact pinned versions are in `requirements.txt` and `pyproject.toml`.

## How to run

GUI
- After installation and running `dmm-setup`, launch the GUI with one of the installed entry points: `docker-monitor-manager` or the shorter alias `dmm`. If you installed the desktop entry, you can also use the desktop menu item named "Docker Monitor Manager" to start the app.

- The GUI is a single-window Tkinter application that lists containers, metrics, and management actions. The embedded terminal and logging panel are available from the main window.

CLI utilities
- The package provides several small CLI helper programs. Each is designed to be simple and scriptable:
	- `dmm-help`: Prints usage and examples for all CLI helpers and commonly used GUI workflows.
	- `dmm-update`: Pulls the latest release from PyPI (if available) and optionally runs post-install setup. Use `--force` to reinstall even if up-to-date.
	- `dmm-doctor`: Runs a set of diagnostic checks against the Docker environment; pass `--fix` to attempt safe, conservative fixes (permission fixes, missing packages, daemon checks).
	- `dmm-config`: Interactive system configuration helper. It inspects system policies like AppArmor/SELinux and can prompt the user for optional changes. Use `--yes` to accept recommended changes non-interactively.
	- `dmm-test`: Creates simple test containers used to verify monitoring, cloning, and resource reporting. Useful flags include `--status` to show current test containers and `--cleanup` to remove them.
	- `dmm-setup`: Performs post-install desktop integration (desktop entry, icons, optional application shortcuts).
	- `dmm-uninstall`: Removes installed files and desktop entries created by `dmm-setup`.

Quick start (recommended):
1. `pip install docker-monitor-manager` (or use `pipx install docker-monitor-manager`)
2. `dmm-setup`
3. `dmm-doctor --fix` (confirm fixes when prompted)
4. (optional) `dmm-test --cpu --memory` to create sample containers
5. `dmm` or open the app from your desktop menu

## README.md highlights (detailed summary)

- Features and UX: The README lists core features (monitoring metrics, inline management actions, cloning policy, embedded terminal, logging) and includes screenshots or examples where appropriate. It describes the expected app behavior during scale events and how clones are labeled and managed so users can identify transient test clones versus primary containers.

- Installation options and recommended workflows: The README documents the three installation paths (PyPI, pipx, source) and recommends `pipx` for CLI-only installations to avoid global package conflicts. It also includes post-installation steps (`dmm-setup`) and links to platform-specific packaging notes.

- CLI reference: Each `dmm-` command is explained with available flags and expected behavior. Examples show a typical admin workflow: install -> integrate desktop -> run doctor -> test containers -> open GUI.

- Troubleshooting: Practical guidance for common problems is provided, including how to resolve Docker permission issues (adding the user to the `docker` group), verifying the Docker daemon state, and using `dmm-doctor` and `dmm-test` for step-by-step debugging. The README encourages running `dmm-doctor` before opening the GUI if the docker environment may be misconfigured.

- Developer notes: The README includes commands for quick import/compile checks, building a distribution with `python -m build`, and a short developer-oriented layout of the source tree to help contributors find entry points and tests.

## Security notes

- Restricted command surface: The embedded terminal widget intentionally restricts input to commands that start with `docker` and the `clear` command. This reduces the risk that an attacker or a mistaken paste executes arbitrary shell commands from within the GUI. The terminal implementation validates and sanitizes inputs before invoking them through the Docker SDK or a subprocess.

- Privileged operations: Some helpers (notably `dmm-config`) may offer to run system-level package manager or policy commands that require `sudo`. These operations are always presented with a clear prompt and must be explicitly approved by the user; `--yes` is an available flag for intentionally non-interactive automation.

- Principle of least privilege: The app aims to use the Docker SDK where possible rather than invoking shell commands. When shell execution is necessary, arguments are validated and executed with minimal privileges. Users are encouraged to review and understand any prompts that request elevated permissions.

- Not a security boundary: While the embedded restrictions improve safety, the project is not designed to be a hardened security boundary against a determined attacker. For high-security environments, prefer audited orchestrators and restricted user policies.

## Troubleshooting (summary)

- Permission errors accessing Docker: If the GUI or CLI reports permission denied errors when talking to the Docker socket, first confirm the Docker daemon is running (`systemctl status docker` on systemd systems). If the daemon is running, add your user to the `docker` group to allow non-root access (`sudo usermod -aG docker $USER`) and re-login. `dmm-doctor --fix` can detect and offer safe fixes for common permission and configuration problems.

- AppArmor/SELinux interference: Security frameworks such as AppArmor (common on Ubuntu) or SELinux (common on Fedora/RHEL) can block container operations or filesystem access required by the app. Use `dmm-config` to inspect current profiles and, if necessary, switch AppArmor to complain mode for Docker (`aa-complain <profile>`) or follow distribution-specific guidance to adjust SELinux booleans. Make such changes only when you understand the security implications.

- Container lifecycle problems: If containers are not starting or clones misbehave, run `dmm-test` to create minimal test containers and validate monitoring and clone behavior. Inspect logs in the GUI's log panel and run `dmm-doctor` for additional diagnostics.

- Crashes and exceptions: Check the application's log view to capture stack traces. If a Python exception originates from the application code, run the quick import/compile checks (`python3 -m py_compile ...` and `python3 -c "import docker_monitor.main as m; print('OK')"`) to confirm your environment's Python packages are intact. When reporting issues, include the output from `dmm-doctor --status` and a copy of the recent application logs.

## Developer quick checks and tests

- Quick syntax test:
	- python3 -m py_compile docker_monitor/*.py

- Quick import test:
	- python3 -c "import docker_monitor.main as m; print('OK')"

- Build releases:
	- pip install build
	- python -m build

## Notes, assumptions and next steps

- Assumptions: This report is based primarily on `README.md` and the repository layout. Where runtime or packaging specifics are not available in code, this report follows the README instructions.
- Suggested next steps (optional): add a minimal CONTRIBUTING.md to document how to run tests and submit patches; add CI for linting and packaging to catch regressions early; add a short quickstart GIF/screenshots to `README.md` for visual onboarding.

---



## Code reference — file-by-file explanation

This document walks through the main Python modules in the repository, explaining their responsibilities, key classes and functions, inputs/outputs, important side-effects, and where to look when changing behavior. The goal is that a developer reading this report can understand the code flow and make targeted edits.

Note: function/method names are shown exactly as in the code to make navigation easy.

1) `docker_monitor/__init__.py`
   - Purpose: package metadata.
   - Key symbols: `__version__`, `__author__`, `__email__`.
   - Where to change: bump `__version__` for releases, update author/contact details.

2) `docker_monitor/main.py`
   - Purpose: simple CLI entrypoint that configures logging and runs the GUI main function.
   - Key actions: sets up a `BufferHandler` for logging (stores logs in memory) and calls `main()` from `docker_monitor.gui.docker_monitor_app` when executed as a script.
   - Where to change: adjust global logging configuration or swap the frontend entrypoint.

3) `docker_monitor/cli/` (CLI helpers)
   - `config.py` (dmm-config)
     - Purpose: interactive system configuration helper to detect and optionally install Docker, and manage AppArmor utilities on Linux.
     - Key functions:
       - `main(argv=None)`: entrypoint, parses `--yes` flag and orchestrates detection/install.
       - `check_docker()`: returns True if Docker binary is available and responds.
       - `install_docker_linux(auto_yes)`, `install_docker_macos(auto_yes)`, `install_docker_windows(auto_yes)`: platform-specific installation flows.
       - `ensure_apparmor_utils_linux(auto_yes)`: ensures `apparmor-utils` present and optionally toggles Docker AppArmor profile.
     - Inputs: user prompts or `--yes` flag. Outputs: installs packages (side-effect) and prints status.
     - Where to change: change install commands, add distro heuristics, or make the script more conservative or more automated.

   - `doctor.py` (dmm-doctor)
     - Purpose: system health checker and optional auto-fixer.
     - Key functions:
       - `main(argv=None)`: entrypoint, supports `--fix` to enable auto-fix.
       - `check_docker_installed()`, `check_docker_running()`, `check_docker_permissions()`, `check_docker_socket()`, `check_docker_service()`, `check_system_resources()`, `check_network_connectivity()`: diagnostic checks that return (bool, message).
       - `fix_docker_permissions(auto_fix)`, `fix_docker_service(auto_fix)`: attempted fixes (may call `sudo` commands).
       - `diagnose_docker_daemon_issues()`: tries to parse journalctl and other outputs to provide probable causes.
     - Inputs: flags (`--fix`, `--verbose`). Outputs: colored terminal diagnostics and may run privileged commands.
     - Where to change: add more checks (e.g., proxy detection), enhance auto-fix logic or change messaging.

   - `help.py` (dmm-help)
     - Purpose: pretty-prints usage and examples for all `dmm-*` commands.
     - Key functions: `main()`, `show_main_help()`, `show_command_help(command)`.
     - Inputs: optional command name argument. Outputs: colored help text only (no side-effects).
     - Where to change: update the help content or add new command docs.

   - `setup.py` (dmm-setup)
     - Purpose: small wrapper that runs `setup_tools/post_install.py` for desktop integration.
     - Key functions: `post_install()` which locates and executes the script.
     - Where to change: alter desktop integration behavior or add Windows/macOS installers.

   - `test.py` (dmm-test)
     - Purpose: helper to create simple test containers for manual testing and CI.
     - Key functions: `create_normal_containers()`, `cleanup_existing_test_containers()`, `show_container_status()`, `main()` with CLI args `--cleanup` and `--status`.
     - Inputs: optional flags; side-effects: pulls images and creates containers with known names (`dmm-test-*`).
     - Where to change: extend test scenarios, add more configurable test images or resource stress options.

   - `update.py` (dmm-update)
     - Purpose: updates the package via pip and runs post-install setup.
     - Key functions: `get_current_version()`, `check_pip_available()`, `get_latest_version()`, `update_package(force=False)`, `main()`.
     - Inputs: user confirmation and `--force` flag. Side-effects: runs `pip install --upgrade` and `dmm-setup`.
     - Where to change: change update sources (GitHub), or support alternate install workflows.

   - `uninstall.py` (dmm-uninstall)
     - Purpose: wrapper that locates and runs `setup_tools/uninstall.py` to remove installed files.
     - Key function: `main()`.
     - Side-effects: executes uninstall script which removes desktop entries and files.

4) `docker_monitor/gui/docker_monitor_app.py` (large GUI)
   - Purpose: main Tkinter application class `DockerMonitorApp` that composes the entire UI and wires managers/widgets.
   - High-level flow:
     - Creates main window, panes, status bar and calls UI composition helpers: `create_control_widgets`, `create_container_widgets`, `create_log_widgets`, `create_terminal_widgets`.
     - Starts periodic updates for containers, networks, images, volumes, logs and dashboard via `after()` scheduling.
     - Delegates domain logic to manager classes (`ContainerManager`, `ImageManager`, `NetworkManager`, `VolumeManager`, `SystemManager`, `PruneManager`, `InfoDisplayManager`).
   - Key methods to know and where to change behavior:
     - UI layout helpers: `create_control_widgets`, `create_container_widgets`, `create_log_widgets`, `create_terminal_widgets` — modify UI structure or controls here.
     - Periodic update hooks: `update_container_list()`, `update_network_list()`, `update_images_list()`, `update_volumes_list()`, `update_logs()`, `update_dashboard()` — change refresh timing or how data is consumed.
     - Action handlers: `run_container_action`, `run_image_action`, `run_network_action`, `run_volume_action`, `run_global_action`, `prune_system`, etc. — these call manager functions that perform Docker SDK calls.
     - Info display delegators: `display_container_info`, `display_image_info`, `display_network_info`, `display_volume_info` — these hand off to manager modules which fetch and format details.
   - Inputs/Outputs: reads from queues and manager fetch functions; writes to Tk widgets and status bar; side-effects include Docker operations when user triggers actions.
   - Where to change: modify UI layout, add new tabs, or change event handlers that trigger manager calls.

5) `docker_monitor/gui/managers/` (managers)
   - `container_manager.py`
     - Purpose: list containers, perform per-container actions, implement global actions like stop-all, and display container info.
     - Key functions:
       - `fetch_all_stats()`: uses `docker_utils.client` and `get_container_stats` to build a stats list.
       - `apply_containers_to_tree(tree, stats_list, ...)`: synchronizes a Treeview with container data.
       - `run_container_action(tree, action)`: invokes Docker SDK methods on the selected container.
       - `run_global_action(action)`: iterates containers and applies lifecycle actions.
       - `stop_all_containers(status_bar_callback, log_callback)`: interactive stop-all implementation using threads and callbacks for UI updates.
       - `display_container_info(info_text, container_name, placeholder_label)`: fetches `container.attrs` and writes formatted details to the info text widget.
     - Inputs/Outputs: interacts with `client` (Docker SDK); updates UI via provided widgets or callbacks.
     - Where to change: change cloning/scale triggers, adjust displayed fields, or add more container actions.

   - `image_manager.py`
     - Purpose: list images, pull images, remove images, and display image details.
     - Key functions: `fetch_images()`, `update_images_tree(...)`, `remove_image(image_id, confirm_callback)`, `pull_image(repo, success_callback)`, `prune_images(...)`, `display_image_info(...)`, `show_image_inspect_modal(...)`.
     - Side-effects: `client.images.pull`, `client.images.remove`, `client.images.prune`.
     - Where to change: modify prune behavior, add progress reporting for pulls, improve image size formatting.

   - `network_manager.py`
     - Purpose: list networks, create/remove networks, connect/disconnect containers, and show network info.
     - Key functions: `fetch_networks()`, `update_network_tree(...)`, `create_network(...)`, `remove_network(...)`, `prune_networks(...)`, `display_network_info(...)`, `connect_container_to_network(...)`, `disconnect_container_from_network(...)`.
     - Side-effects: `client.networks.create/remove/connect/disconnect`.
     - Where to change: add support for advanced driver options or IPv6/IPAM adjustments.

   - `volume_manager.py`
     - Purpose: list volumes, remove/prune volumes, display inspect output, and show which containers use volumes.
     - Key functions: `fetch_volumes()`, `update_volumes_tree(...)`, `remove_volume(name, update_callback)`, `prune_volumes(...)`, `show_volume_inspect_modal(...)`, `display_volume_info(...)`.
     - Side-effects: `client.volumes.prune()` and `client.volumes.get(...).remove()`.
     - Where to change: add safe checks before deletion (e.g., detect active mounts), stream large JSON responses to a file instead of modal.

   - `system_manager.py`
     - Purpose: dashboard metrics, system prune orchestration, system info and disk usage, export full system report.
     - Key functions: `update_dashboard(dash_vars)`, `prune_system(status_bar, refresh_callback)`, `show_system_info(parent)`, `refresh_docker_info(docker_info_text, status_bar)`, `check_disk_usage(disk_usage_text, status_bar)`, `export_system_report(...)`.
     - Inputs/Outputs: calls `client.info()`, `client.df()`, performs pruning operations and writes a human-readable report file.
     - Where to change: extend exported report details, include health-check output or CI-friendly JSON output.

   - `prune_manager.py`
     - Purpose: small helpers to prune containers/images/networks and remove stopped containers. Uses background threads to avoid blocking the GUI.
     - Key functions: `prune_containers`, `prune_images`, `prune_networks`, `remove_all_stopped_containers`.
     - Where to change: centralize prune confirmation or add dry-run mode.

   - `info_display_manager.py`
     - Purpose: small helpers to write formatted info into the Info tab widgets.
     - Key functions: `add_info_line(info_text, key, value)`, `show_info_error(...)`, `show_info_placeholder(...)`, `update_text_widget(...)`.

6) `docker_monitor/gui/widgets/` (UI widgets)
   - `copy_tooltip.py` — `CopyTooltip` class
     - Purpose: display a small temporary tooltip near the cursor when the user copies an ID.
     - Key methods: `show(text, x=None, y=None)`, `_fade_out()`, `_destroy()`.
     - Where to change: adjust display duration or style.

   - `docker_terminal.py` — `DockerTerminal` widget
     - Purpose: embedded terminal focused on executing `docker` commands safely.
     - Key features and methods:
       - Input handling with protected prompt (`input_start` mark) and history navigation: `handle_history_up`, `handle_history_down`.
       - Security: only allow commands starting with `docker` (or `clear`). Rejected commands print a security message.
       - Command execution in background thread: `_execute_command(command_parts)` that pushes output lines to a queue; `_poll_output()` drains the queue and appends lines to the Text widget.
       - Tab completion for a predefined list of docker subcommands via `handle_tab_completion`.
       - Key bindings for Ctrl+L (clear), Ctrl+C (copy selection), and other navigation.
     - Inputs/Outputs: executes subprocess commands, writes output into widget; side-effect: running arbitrary `docker` CLI commands (limited by the user permissions and Docker socket access).
     - Where to change: extend completion list, add auto-suggestions, integrate with Docker SDK instead of shelling out for richer behavior.

   - `ui_components.py` — `UIComponents` and `MousewheelHandler`
     - Purpose: shared UI styling, creation helpers (stat cards, control buttons), and mousewheel binding helpers.
     - Key methods: `setup_styles(app_instance)`, `create_control_button(...)`, `create_stat_card(...)`, `add_help_section(...)`, `add_info_line(...)`, `show_info_error(...)`, `show_info_placeholder(...)`.
     - Where to change: central place to change theme, fonts, and common widgets.

7) `docker_monitor/utils/` (utilities)
   - `docker_utils.py`
     - Purpose: central Docker SDK client, locks, queues, monitoring logic and scaling logic used by the GUI managers and background threads.
     - Key variables and objects exported:
       - `client`: docker.from_env() client used across the app.
       - `docker_lock`: threading.Lock() to serialize Docker SDK calls.
       - `stats_queue`, `network_refresh_queue`, `logs_stream_queue`, `events_queue`: queues for background threads to communicate with GUI.
       - Limits & constants: `CPU_LIMIT`, `RAM_LIMIT`, `CLONE_NUM`, `SLEEP_TIME`.
       - Helper functions: `calculate_cpu_percent(stats)`, `calculate_ram_percent(stats)`, `get_container_stats(container)`.
       - Scaling helpers: `is_clone_container(container)`, `get_parent_container_name(container)`, `delete_clones(container, all_containers)`, `scale_container(container, all_containers)` — cloning is implemented by committing the container to an image and running a new container from that image with labels to mark it as a clone.
       - Background threads: `monitor_thread()` (polls containers and applies auto-scale) and `docker_events_listener()` (listens to Docker events and pushes updates to queues).
     - Important notes:
       - `client` is created at import time and the module calls `client.ping()`; if Docker isn't available, the process exits — this can make importing the package in non-Docker environments fail. Consider catching this and failing more gracefully for CLI-only tools.
       - The auto-scaling approach uses `commit()` and `run()` to create clones — this may produce transient images; the cleanup logic uses `docker_cleanup()` and `client.images.prune()` to reclaim space.
     - Where to change: tuning `CPU_LIMIT`, `RAM_LIMIT`, clone policy (`CLONE_NUM`), or replace commit/run cloning with more robust cloning strategies (volumes, bind mounts, environment preservation).

   - `buffer_handler.py`
     - Purpose: custom logging handler `BufferHandler` that stores recent logs in `log_buffer` for the GUI and export reports.
     - Key objects: `log_buffer` (deque), `BufferHandler` (logging.Handler).
     - Where to change: adjust buffer size or log format.

8) `setup_tools/` (packaging scripts; not runtime)
   - `post_install.py`, `uninstall.py`, `create_icons.sh`, and `icons/` — scripts and assets used by `dmm-setup` and packaging. They handle generating icons and writing desktop `.desktop` entries on Linux.

How to navigate and modify logic safely

- Threading and locks: Docker SDK calls are typically guarded by `docker_lock` to avoid race conditions. When adding background work that touches `client`, reuse `docker_lock`.
- UI updates from threads: managers use `status_bar.after(...)` or pass callbacks into thread worker functions to update the UI on the main thread. Avoid manipulating Tk widgets directly from background threads.
- Long-running operations: image pulls, commits and prunes are run in background threads to keep the UI responsive — follow the same pattern when adding new long-running actions.
- Side-effects & permissions: many operations (install, service start, add user to docker group) invoke `sudo` or require privileged access; CLI helpers make prompts and require explicit confirmation.

This concludes the in-repo code reference. If you'd like, I can now:

- Insert a small Mermaid or ASCII diagram showing high-level component interactions (GUI -> Managers -> utils -> Docker SDK).
- Auto-generate a markdown table of files and top-level exported symbols for quick indexing.
- Expand any particular file's documentation with line-level notes or an annotated outline showing where each function is defined.

---

# Docker Monitor Manager — Project Report

## General information

Repository: docker-monitor-manager

Purpose: Docker Monitor Manager is a small native desktop application and set of CLI utilities for monitoring and managing Docker containers. It provides a Tkinter-based GUI for live container statistics, basic management actions (stop/pause/restart/remove), an embedded restricted terminal for running docker commands, auto-scaling behavior (lightweight clones for overloaded containers), logging, and a suite of CLI helpers for system configuration, health checks, test environments, installation/setup, updates and uninstallation.

Language & platform: Python (3.8+). The GUI uses Tkinter. The project targets Linux, macOS and Windows with platform-specific packaging notes included in the repository.

Key runtime dependencies: docker (Python SDK), Pillow (optional for icon generation). See `requirements.txt` and `pyproject.toml` for full dependency pins.

## Project structure and file concepts

Top-level files
- `README.md` — User-facing documentation, usage examples, and command reference (summarized in this report).
- `setup.py`, `pyproject.toml`, `requirements.txt` — Packaging and dependency metadata.
- `report.md` — This report (project overview and usage summary).

Main package: `docker_monitor/`
- `__init__.py` — Package metadata (version, author).
- `main.py` — Application entry point for the GUI; also used for the console entry point when installed (`docker-monitor-manager` / `dmm`).

CLI tools: `docker_monitor/cli/`
- `config.py` — `dmm-config` helper to detect / configure Docker and optional AppArmor/SELinux adjustments.
- `doctor.py` — `dmm-doctor` health checker and conservative auto-fixer for common Docker problems.
- `help.py` — `dmm-help` — displays documentation and usage for the CLI tools.
- `setup.py` — `dmm-setup` — post-installation setup (desktop entry and icons).
- `test.py` — `dmm-test` — test environment creator (creates containers used to verify monitoring).
- `update.py` — `dmm-update` — auto-update helper that pulls latest from PyPI and runs setup.
- `uninstall.py` — `dmm-uninstall` — complete uninstaller that removes installed files and desktop entries.

GUI: `docker_monitor/gui/`
- `docker_monitor_app.py` — The Tkinter application bootstrap and main window.
- `managers/` — A collection of managers handling different responsibilities in the UI:
	- `container_manager.py` — Listing containers, actions (stop, pause, restart, remove), clone management, and live stats.
	- `image_manager.py`, `network_manager.py`, `volume_manager.py`, `system_manager.py`, `prune_manager.py` — Supporting management screens and actions.
	- `info_display_manager.py` — Manages the information panels and logs.
- `widgets/` — Reusable UI widgets used in the app (embedded terminal, tooltips, common UI components).

Utilities: `docker_monitor/utils/`
- `docker_utils.py` — Thin wrappers around the Docker Python SDK used by the GUI and CLI tools.
- `buffer_handler.py` — Utilities for handling streaming logs and buffers used in the app.

Setup tools: `setup_tools/`
- Scripts and helper files for packaging, desktop entries, icons and post-install actions.

Tests: `tests/` — Test utilities and test cases (if present). These provide basic compile/import checks and test container lifecycle tests via `dmm-test`.

Other supporting files
- `MANIFEST.in`, `LICENSE`, `README.md` — Packaging and documentation artifacts for distribution.

## Project structure

This section summarizes the repository layout, where to find key functionality, and how components interact at a high level. The layout follows a conventional Python package structure with additional helper scripts for packaging and desktop integration.

- Top-level files
	- `README.md`, `report.md`, `LICENSE`, `MANIFEST.in`, `pyproject.toml`, `setup.py`, `requirements.txt` — documentation and packaging metadata. Use these for installation, release builds and developer guidance.

- Main package: `docker_monitor/`
	- `__init__.py` — package metadata and exported version information.
	- `main.py` — application entry point used by both the GUI launcher and the console entry point. This file initializes logging, config, and the main application object.

- CLI helpers: `docker_monitor/cli/`
	- Each module (`config.py`, `doctor.py`, `help.py`, `setup.py`, `test.py`, `update.py`, `uninstall.py`) implements a focused command-line utility. These are wired to console entry points (installed as `dmm-*` programs) and are lightweight, scriptable helpers that reuse shared utilities.

- GUI: `docker_monitor/gui/`
	- `docker_monitor_app.py` — bootstrap for the Tkinter UI; builds the main window and wires the managers and widgets together.
	- `managers/` — controller-style modules that encapsulate discrete responsibilities (container listing and actions, image/network/volume screens, system info, pruning, and info/log display). Managers coordinate the UI and call into the utility layer to perform work.
	- `widgets/` — reusable UI components (embedded terminal, copy-tooltips, shared UI controls) used across the GUI screens.

- Utilities: `docker_monitor/utils/`
	- `docker_utils.py` — common, thin wrappers around the Docker Python SDK used by both the GUI and CLI tools. This module centralizes Docker API calls, error handling and small adapters that make the rest of the code easier to test.
	- `buffer_handler.py` — streaming and buffer utilities for log capture and terminal I/O.

- Packaging / Helpers: `setup_tools/`
	- Contains icon creation scripts, `.desktop` template files and a `post_install.py` helper used by `dmm-setup` to integrate the app into desktop environments. These are not part of the runtime package but are used during packaging and post-install steps.

- Tests: `tests/`
	- Unit or integration helpers and test cases (where present). The `dmm-test` helper creates transient containers used by the test suite and by developers to validate monitoring features manually.

- Build artifacts: `build/` and `docker_monitor_manager.egg-info/`
	- Generated by packaging tools. Not committed for source edits; these are useful to inspect for release metadata when building locally.

How components interact (concise):

- The GUI (`docker_monitor_app.py`) composes managers and widgets. Managers call into `docker_utils.py` to query container lists, fetch stats and execute Docker operations. `buffer_handler.py` is used when streaming logs or piping command output into the embedded terminal widget.
- CLI helpers reuse `docker_utils.py` and shared helpers so the same logic is available to headless users and automated scripts. This avoids duplication between the GUI and CLI.
- `setup_tools/` is only used during packaging and the `dmm-setup` step; its scripts produce icons and desktop entries so the GUI can be launched from the desktop environment.

Where to make common changes

- To change container metrics or sampling frequency: edit the container manager implementation in `docker_monitor/gui/managers/container_manager.py`.
- To alter cloning/auto-scaling policy: find the scaling logic in the container manager and the Docker helper functions in `docker_monitor/utils/docker_utils.py` that create/manage clones.
- To add or modify CLI behavior: edit the corresponding module in `docker_monitor/cli/` and update entry point mappings in `setup.py` or `pyproject.toml`.

This `Project structure` section is intended as a quick orientation for developers and maintainers. For code-level navigation, search for names like `container_manager`, `docker_utils` and `docker_monitor_app` which are central integration points.

## What this project does (summary)

This project provides both a graphical desktop application and a set of command-line utilities for monitoring and managing Docker resources with a focus on simplicity and safety. Key capabilities include:

- Live container monitoring: The GUI displays per-container resource metrics such as CPU percentage, memory usage, and basic I/O statistics. Metrics are updated at a short interval to give the user near-real-time visibility into container behavior without requiring external monitoring stacks.

- Lightweight auto-scaling: When a container exceeds configured resource thresholds, the application can automatically create lightweight clones of that container to share load. Clone lifecycle is managed by a simple policy (scale-up when overloaded, scale-down when underutilized) to avoid runaway resource consumption. Cloning is intended for short-lived relief and testing, not as a production replacement for orchestrators.

- In-app container management: From the UI users can perform common actions such as stop, pause, unpause, restart and remove. These actions are performed through the Docker Python SDK and are presented with confirmation dialogs to reduce accidental destructive operations.

- Restricted embedded terminal: A terminal widget embedded in the GUI accepts only a limited set of safe commands (those that begin with `docker` and the `clear` command). This minimizes the risk of arbitrary command execution while enabling power users to run container commands from within the app.

- Live application logs: The app surfaces its internal logs and recent Docker events in an integrated log view. This helps with troubleshooting and understanding recent actions (for example, scale events or failed API calls).

- CLI helper utilities: A suite of small command-line programs (prefixed with `dmm-`) support installation/post-install setup, health checks, automated fixes for common issues, test environment creation (for validating monitoring features), updates, and uninstallation. These tools let advanced users script and automate common maintenance tasks.

## How to install

The project supports several common installation methods so you can choose between a system-wide library install, an isolated CLI install, or a developer/source installation. All methods have the same runtime prerequisites (Python 3.8+, and a running Docker Engine).

1) Install from PyPI (stable release):
	- This is the simplest method for end users. It installs the package and exposes the CLI entry points.
	- Example: `pip install docker-monitor-manager`

2) Install with pipx (recommended for isolated CLI installs):
	- `pipx` creates a per-application virtual environment and puts the CLI into your PATH without touching your system Python packages.
	- Example: `pipx install docker-monitor-manager`

3) Install from source (developer / local install):
	- Useful if you want to modify the code or use the latest master branch.
	- Example:
	  - `git clone <repo>`
	  - `cd docker-monitor-manager`
	  - `pip install .`

Post-install step (desktop integration):
- Run `dmm-setup` after installation to create the desktop entry and install icons so the GUI appears in your desktop environment's application menu. On Linux this creates a `.desktop` file in the appropriate user applications directory.

Runtime prerequisites and notes:
- Python 3.8 or newer.
- Docker Engine must be installed and running (daemon active).
- On Linux, to allow non-root Docker access: `sudo usermod -aG docker $USER` and then re-login or run `newgrp docker`.
- The application depends on the Python `docker` package (Docker SDK) and optionally `Pillow` for icon manipulation. Exact pinned versions are in `requirements.txt` and `pyproject.toml`.

## How to run

GUI
- After installation and running `dmm-setup`, launch the GUI with one of the installed entry points: `docker-monitor-manager` or the shorter alias `dmm`. If you installed the desktop entry, you can also use the desktop menu item named "Docker Monitor Manager" to start the app.

- The GUI is a single-window Tkinter application that lists containers, metrics, and management actions. The embedded terminal and logging panel are available from the main window.

CLI utilities
- The package provides several small CLI helper programs. Each is designed to be simple and scriptable:
	- `dmm-help`: Prints usage and examples for all CLI helpers and commonly used GUI workflows.
	- `dmm-update`: Pulls the latest release from PyPI (if available) and optionally runs post-install setup. Use `--force` to reinstall even if up-to-date.
	- `dmm-doctor`: Runs a set of diagnostic checks against the Docker environment; pass `--fix` to attempt safe, conservative fixes (permission fixes, missing packages, daemon checks).
	- `dmm-config`: Interactive system configuration helper. It inspects system policies like AppArmor/SELinux and can prompt the user for optional changes. Use `--yes` to accept recommended changes non-interactively.
	- `dmm-test`: Creates simple test containers used to verify monitoring, cloning, and resource reporting. Useful flags include `--status` to show current test containers and `--cleanup` to remove them.
	- `dmm-setup`: Performs post-install desktop integration (desktop entry, icons, optional application shortcuts).
	- `dmm-uninstall`: Removes installed files and desktop entries created by `dmm-setup`.

Quick start (recommended):
1. `pip install docker-monitor-manager` (or use `pipx install docker-monitor-manager`)
2. `dmm-setup`
3. `dmm-doctor --fix` (confirm fixes when prompted)
4. (optional) `dmm-test --cpu --memory` to create sample containers
5. `dmm` or open the app from your desktop menu

## README.md highlights (detailed summary)

- Features and UX: The README lists core features (monitoring metrics, inline management actions, cloning policy, embedded terminal, logging) and includes screenshots or examples where appropriate. It describes the expected app behavior during scale events and how clones are labeled and managed so users can identify transient test clones versus primary containers.

- Installation options and recommended workflows: The README documents the three installation paths (PyPI, pipx, source) and recommends `pipx` for CLI-only installations to avoid global package conflicts. It also includes post-installation steps (`dmm-setup`) and links to platform-specific packaging notes.

- CLI reference: Each `dmm-` command is explained with available flags and expected behavior. Examples show a typical admin workflow: install -> integrate desktop -> run doctor -> test containers -> open GUI.

- Troubleshooting: Practical guidance for common problems is provided, including how to resolve Docker permission issues (adding the user to the `docker` group), verifying the Docker daemon state, and using `dmm-doctor` and `dmm-test` for step-by-step debugging. The README encourages running `dmm-doctor` before opening the GUI if the docker environment may be misconfigured.

- Developer notes: The README includes commands for quick import/compile checks, building a distribution with `python -m build`, and a short developer-oriented layout of the source tree to help contributors find entry points and tests.

## Security notes

- Restricted command surface: The embedded terminal widget intentionally restricts input to commands that start with `docker` and the `clear` command. This reduces the risk that an attacker or a mistaken paste executes arbitrary shell commands from within the GUI. The terminal implementation validates and sanitizes inputs before invoking them through the Docker SDK or a subprocess.

- Privileged operations: Some helpers (notably `dmm-config`) may offer to run system-level package manager or policy commands that require `sudo`. These operations are always presented with a clear prompt and must be explicitly approved by the user; `--yes` is an available flag for intentionally non-interactive automation.

- Principle of least privilege: The app aims to use the Docker SDK where possible rather than invoking shell commands. When shell execution is necessary, arguments are validated and executed with minimal privileges. Users are encouraged to review and understand any prompts that request elevated permissions.

- Not a security boundary: While the embedded restrictions improve safety, the project is not designed to be a hardened security boundary against a determined attacker. For high-security environments, prefer audited orchestrators and restricted user policies.

## Troubleshooting (summary)

- Permission errors accessing Docker: If the GUI or CLI reports permission denied errors when talking to the Docker socket, first confirm the Docker daemon is running (`systemctl status docker` on systemd systems). If the daemon is running, add your user to the `docker` group to allow non-root access (`sudo usermod -aG docker $USER`) and re-login. `dmm-doctor --fix` can detect and offer safe fixes for common permission and configuration problems.

- AppArmor/SELinux interference: Security frameworks such as AppArmor (common on Ubuntu) or SELinux (common on Fedora/RHEL) can block container operations or filesystem access required by the app. Use `dmm-config` to inspect current profiles and, if necessary, switch AppArmor to complain mode for Docker (`aa-complain <profile>`) or follow distribution-specific guidance to adjust SELinux booleans. Make such changes only when you understand the security implications.

- Container lifecycle problems: If containers are not starting or clones misbehave, run `dmm-test` to create minimal test containers and validate monitoring and clone behavior. Inspect logs in the GUI's log panel and run `dmm-doctor` for additional diagnostics.

- Crashes and exceptions: Check the application's log view to capture stack traces. If a Python exception originates from the application code, run the quick import/compile checks (`python3 -m py_compile ...` and `python3 -c "import docker_monitor.main as m; print('OK')"`) to confirm your environment's Python packages are intact. When reporting issues, include the output from `dmm-doctor --status` and a copy of the recent application logs.

## Developer quick checks and tests

- Quick syntax test:
	- python3 -m py_compile docker_monitor/*.py

- Quick import test:
	- python3 -c "import docker_monitor.main as m; print('OK')"

- Build releases:
	- pip install build
	- python -m build

## Notes, assumptions and next steps

- Assumptions: This report is based primarily on `README.md` and the repository layout. Where runtime or packaging specifics are not available in code, this report follows the README instructions.
- Suggested next steps (optional): add a minimal CONTRIBUTING.md to document how to run tests and submit patches; add CI for linting and packaging to catch regressions early; add a short quickstart GIF/screenshots to `README.md` for visual onboarding.

---

