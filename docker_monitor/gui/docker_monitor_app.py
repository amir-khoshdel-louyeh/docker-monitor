"""
Docker Monitor Application
Main application class for monitoring and managing Docker containers.
"""

import docker
import time
import logging
import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog, messagebox
import json
import os
import threading
import queue
import subprocess
from datetime import datetime
from pathlib import Path

# Import custom modules
from docker_monitor.utils.buffer_handler import log_buffer
from docker_monitor.gui.widgets.copy_tooltip import CopyTooltip
from docker_monitor.gui.widgets.docker_terminal import DockerTerminal
from docker_monitor.gui.widgets.ui_components import UIComponents, MousewheelHandler
from docker_monitor.gui.managers.container_manager import ContainerManager
from docker_monitor.gui.managers.network_manager import NetworkManager
from docker_monitor.gui.managers.image_manager import ImageManager
from docker_monitor.gui.managers.volume_manager import VolumeManager
from docker_monitor.gui.managers.system_manager import SystemManager
from docker_monitor.gui.managers.prune_manager import PruneManager
from docker_monitor.gui.managers.info_display_manager import InfoDisplayManager
from docker_monitor.utils.docker_utils import (
    client,
    docker_lock,
    stats_queue,
    manual_refresh_queue,
    network_refresh_queue,
    logs_stream_queue,
    events_queue,
    CPU_LIMIT,
    RAM_LIMIT,
    CLONE_NUM,
    SLEEP_TIME,
    calculate_cpu_percent,
    calculate_ram_percent,
    get_container_stats,
    delete_clones,
    docker_cleanup,
    scale_container,
    monitor_thread,
    docker_events_listener
)


class DockerMonitorApp(tk.Tk):
    def __init__(self):
        # IMPORTANT: className must EXACTLY match StartupWMClass in .desktop file
        # This is critical for window manager to show the correct icon in taskbar
        super().__init__(className="docker-monitor-manager")
        
        # Set window title
        self.title("Docker Monitor Manager")
        
        # Set window icon BEFORE showing the window
        self._set_window_icon()
        
        # Additional window manager hints
        try:
            # Set WM_CLIENT_MACHINE for better window identification
            import socket
            hostname = socket.gethostname()
            self.tk.call('wm', 'client', self._w, hostname)
        except Exception as e:
            logging.debug(f"Could not set WM_CLIENT: {e}")
        
        # Set window role for better window management
        try:
            self.tk.call('wm', 'group', self._w, self._w)
        except Exception as e:
            logging.debug(f"Could not set WM_GROUP: {e}")
            logging.debug(f"Could not set WM_ROLE: {e}")
        
        # Get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        # Set geometry to cover the entire screen
        self.geometry(f"{screen_width}x{screen_height}+0+0")

        self.configure(bg='#1e2a35')

        self.log_update_idx = 0
        
        # Initialize copy tooltip for professional hints
        self.copy_tooltip = CopyTooltip(self)
        
        # Initialize default resource limits
        self.default_mem_limit = '512m'
        self.default_cpu_limit = '1.0'

        # Setup UI styles using UIComponents
        UIComponents.setup_styles(self)

        # --- Main Layout ---
        # The main split is now horizontal: Controls on the left, everything else on the right.
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Left Pane: Controls ---
        controls_frame = ttk.Labelframe(main_pane, text="Controls", width=150)
        main_pane.add(controls_frame, weight=0)

        # --- Right Pane (Vertical Split) ---
        right_pane = ttk.PanedWindow(main_pane, orient=tk.VERTICAL)
        main_pane.add(right_pane, weight=1)

        # --- Top-Right: Containers ---
        containers_frame = ttk.Labelframe(right_pane, text="Containers", style='Containers.TLabelframe')
        right_pane.add(containers_frame, weight=1)

        # --- Bottom-Right: Logs and Terminal ---
        bottom_right_frame = ttk.Frame(right_pane)
        right_pane.add(bottom_right_frame, weight=1)

        bottom_pane = ttk.PanedWindow(bottom_right_frame, orient=tk.HORIZONTAL)
        bottom_pane.pack(fill=tk.BOTH, expand=True)
        logs_frame = ttk.Labelframe(bottom_pane, text="Application Logs", width=400)
        terminal_frame = ttk.Labelframe(bottom_pane, text="Docker Terminal", width=400)
        bottom_pane.add(logs_frame, weight=1)
        bottom_pane.add(terminal_frame, weight=1)
        
        # Store references for sash positioning
        self._main_pane = main_pane
        self._right_pane = right_pane
        self._bottom_pane = bottom_pane
        
        # Set the initial sash positions for a balanced layout
        # Wait a bit longer to ensure window is fully rendered
        def set_sash_positions():
            try:
                # Force update to ensure widgets are rendered
                self.update_idletasks()
                
                # Left panel (controls) should be narrow
                self._main_pane.sashpos(0, 170)
                
                # Top section (containers/tabs) should take about 60% of vertical space
                # Use actual window height instead of screen height
                actual_height = self.winfo_height() - 40  # subtract padding
                self._right_pane.sashpos(0, int(actual_height * 0.60))
                
                # Bottom pane (logs/terminal) should be 50-50 horizontal split
                # Calculate based on actual available width
                actual_width = self.winfo_width() - 170 - 40  # subtract controls and padding
                self._bottom_pane.sashpos(0, actual_width // 2)
            except Exception as e:
                logging.error(f"Error setting sash positions: {e}")
        
        # Use longer delay and update again for stability
        self.after(300, set_sash_positions)
        self.after(600, set_sash_positions)  # Second call to ensure it sticks

        # --- Status Bar ---
        self.status_bar = tk.Label(
            self, 
            text="Ready | 🐳 Docker Monitor Manager", 
            bd=1, 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            bg='#1e2a35',
            fg='#00ADB5',
            font=('Segoe UI', 9),
            padx=10,
            pady=5
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # --- Widgets ---
        self.create_control_widgets(controls_frame)
        self.create_container_widgets(containers_frame)
        self.create_log_widgets(logs_frame)
        self.create_terminal_widgets(terminal_frame)

        # --- Start background tasks ---
        self.update_container_list()
        # Start network update loop (keeps network tab fresh)
        self.update_network_list()
        # Start images update loop
        self.update_images_list()
        # Start volumes update loop
        self.update_volumes_list()
        self.update_logs()
        
        # Update status bar with counts
        self.update_status_bar()

    def _set_window_icon(self):
        """Set window icon from installed icon files or package assets."""
        import sys
        import platform
        
        try:
            # Try different icon paths in order of preference
            icon_paths = []
            
            # Get the package directory
            pkg_dir = Path(__file__).parent.parent
            
            if platform.system() == "Linux":
                # 1. Try system-installed icons first (from ~/.local/share/icons)
                home = Path.home()
                for size in [64, 48, 128, 256]:
                    icon_paths.append(home / f".local/share/icons/hicolor/{size}x{size}/apps/docker-monitor-manager.png")
                
                # 2. Try package assets (bundled with package)
                for size in [64, 48, 128, 256, 512]:
                    icon_paths.append(pkg_dir / f"assets/docker-monitor-manager-{size}x{size}.png")
                icon_paths.append(pkg_dir / "assets/icon.png")
                
                # 3. Try setup_tools icons (during development)
                icon_paths.append(pkg_dir.parent / "setup_tools/icons/docker-monitor-manager-64x64.png")
                icon_paths.append(pkg_dir.parent / "setup_tools/icons/docker-monitor-manager-48x48.png")
                
            elif platform.system() == "Windows":
                # Windows ICO file
                home = Path.home()
                icon_paths.append(home / ".icons/docker-monitor-manager.ico")
                icon_paths.append(pkg_dir / "assets/docker-monitor-manager.ico")
                icon_paths.append(pkg_dir.parent / "setup_tools/icons/docker-monitor-manager.ico")
                
            elif platform.system() == "Darwin":
                # macOS - use PNG since Tkinter doesn't support ICNS directly
                for size in [128, 64, 48]:
                    icon_paths.append(pkg_dir / f"assets/docker-monitor-manager-{size}x{size}.png")
                icon_paths.append(pkg_dir.parent / f"setup_tools/icons/docker-monitor-manager-{size}x{size}.png")
            
            # Try to load the first available icon
            for icon_path in icon_paths:
                if icon_path.exists():
                    try:
                        if platform.system() == "Windows" and icon_path.suffix == '.ico':
                            # Use iconbitmap for Windows ICO files
                            self.iconbitmap(str(icon_path))
                        else:
                            # Use PhotoImage for PNG files (Linux/macOS)
                            try:
                                # Try with PIL first (better quality)
                                from PIL import Image, ImageTk
                                img = Image.open(icon_path)
                                photo = ImageTk.PhotoImage(img)
                                self.iconphoto(True, photo)
                                # Keep a reference to prevent garbage collection
                                self._icon_photo = photo
                            except ImportError:
                                # Fallback to tkinter PhotoImage (no PIL)
                                photo = tk.PhotoImage(file=str(icon_path))
                                self.iconphoto(True, photo)
                                # Keep a reference to prevent garbage collection
                                self._icon_photo = photo
                        
                        logging.debug(f"Window icon set from: {icon_path}")
                        return
                    except Exception as e:
                        logging.debug(f"Failed to load icon from {icon_path}: {e}")
                        continue
            
            logging.warning("No window icon found, using default")
            
        except Exception as e:
            logging.error(f"Error setting window icon: {e}")

    def _create_control_button(self, parent, text, bg_color, command, fg_color='white', width=15):
        """Wrapper for UIComponents.create_control_button for backward compatibility."""
        return UIComponents.create_control_button(parent, text, bg_color, command, fg_color, width)

    def create_control_widgets(self, parent):
        # Create a canvas with scrollbar for controls
        canvas = tk.Canvas(parent, bg='#222831', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel scrolling for controls (same as Settings tab)
        def _controls_scroll(event):
            if canvas.yview() != (0.0, 1.0):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        def _controls_scroll_linux_up(event):
            if canvas.yview() != (0.0, 1.0):
                canvas.yview_scroll(-1, "units")
            return "break"
        
        def _controls_scroll_linux_down(event):
            if canvas.yview() != (0.0, 1.0):
                canvas.yview_scroll(1, "units")
            return "break"
        
        canvas.bind('<MouseWheel>', _controls_scroll)
        canvas.bind('<Button-4>', _controls_scroll_linux_up)
        canvas.bind('<Button-5>', _controls_scroll_linux_down)

        # Recursive function to bind mousewheel to all child widgets
        def bind_controls_to_mousewheel(widget):
            widget.bind('<MouseWheel>', _controls_scroll)
            widget.bind('<Button-4>', _controls_scroll_linux_up)
            widget.bind('<Button-5>', _controls_scroll_linux_down)
            for child in widget.winfo_children():
                bind_controls_to_mousewheel(child)
        
        # Bind after all widgets are created
        self.after(100, lambda: bind_controls_to_mousewheel(scrollable_frame))
        
        # Use scrollable_frame as the parent for all controls
        parent = scrollable_frame
        
        # --- Individual Actions Section ---
        # Keep the original frame and button ordering. We'll put per-tab
        # action panels inside this frame so the layout stays identical.
        individual_actions_frame = ttk.Frame(parent)
        individual_actions_frame.pack(pady=5, padx=10, fill=tk.X)

        # --- Selected Container Section (at the top of actions frame) ---
        self.selected_section_frame = ttk.Frame(individual_actions_frame)
        self.selected_section_frame.pack(pady=(5, 10), padx=5, fill=tk.X)
        
        ttk.Label(self.selected_section_frame, text="Selected Item", font=('Segoe UI', 9)).pack(anchor='w')
        self.selected_container_label = ttk.Label(self.selected_section_frame, text="None", font=('Segoe UI', 10, 'bold'), foreground=self.ACCENT_COLOR)
        self.selected_container_label.pack(pady=5)

        # Container action panel (packed by default)
        self.container_actions_panel = ttk.Frame(individual_actions_frame)
        self.container_actions_panel.pack(fill=tk.X)

        # Container actions with better organization
        actions = [
            ('▶️ Start', '#219653', 'start'),      # Green - Start
            ('⏹️ Stop', '#d85000', 'stop'),        # Orange - Stop
            ('🔄 Restart', '#2471a3', 'restart'),  # Blue - Restart
            ('⏸️ Pause', '#d4c100', 'pause'),      # Yellow - Pause
            ('▶️ Unpause', '#00ADB5', 'unpause'),  # Teal - Unpause
            ('🗑️ Remove', '#b80000', 'remove'),    # Red - Remove
        ]

        for label, color, action in actions:
            fg = 'black' if color == '#d4c100' else 'white'
            btn = self._create_control_button(
                self.container_actions_panel,
                label,
                color,
                lambda a=action: self.run_container_action(a),
                fg
            )
            btn.pack(fill=tk.X, expand=False, pady=2, padx=5)

        # Network action panel with icons
        self.network_actions_panel = ttk.Frame(individual_actions_frame)
        net_actions = [
            ('🔍 Inspect', '#6c757d', 'inspect'),
            ('🗑️ Remove', '#b80000', 'remove'),
            ('➕ Create', '#2d6a4f', 'create'),
            ('🔗 Connect', '#1b4965', 'connect'),
            ('❌ Disconnect', '#9a031e', 'disconnect'),
            ('🧹 Prune', '#6c757d', 'prune')
        ]
        for label, color, action in net_actions:
            btn = self._create_control_button(
                self.network_actions_panel,
                label,
                color,
                lambda a=action: self.run_network_action(a)
            )
            btn.pack(fill=tk.X, expand=False, pady=2, padx=5)

        # Images action panel with icons
        self.images_actions_panel = ttk.Frame(individual_actions_frame)
        img_actions = [
            ('🔍 Inspect', '#6c757d', 'inspect'),
            ('🗑️ Remove', '#b80000', 'remove'),
            ('⬇️ Pull', '#2d6a4f', 'pull'),
            ('🏷️ Tag', '#00ADB5', 'tag')
        ]
        for label, color, action in img_actions:
            btn = self._create_control_button(
                self.images_actions_panel,
                label,
                color,
                lambda a=action: self.run_image_action(a)
            )
            btn.pack(fill=tk.X, expand=False, pady=2, padx=5)

        # Volumes action panel with icons
        self.volumes_actions_panel = ttk.Frame(individual_actions_frame)
        vol_actions = [
            ('🔍 Inspect', '#6c757d', 'inspect'),
            ('🗑️ Remove', '#b80000', 'remove'),
            ('🧹 Prune', '#6c757d', 'prune'),
            ('➕ Create', '#2d6a4f', 'create')
        ]
        for label, color, action in vol_actions:
            btn = self._create_control_button(
                self.volumes_actions_panel,
                label,
                color,
                lambda a=action: self.run_volume_action(a)
            )
            btn.pack(fill=tk.X, expand=False, pady=2, padx=5)

        # Dashboard action panel
        self.dashboard_actions_panel = ttk.Frame(individual_actions_frame)
        
        # Warning label
        warning_label = tk.Label(
            self.dashboard_actions_panel,
            text="⚠️  Use with caution!",
            font=('Segoe UI', 8, 'italic'),
            fg='#ff6b6b',
            bg=self.FRAME_BG
        )
        warning_label.pack(pady=(5, 10), padx=5)
        
        dash_actions = [
            ('🔄 Refresh', '#00ADB5', 'refresh'),
            ('🗑️ Prune System', '#b80000', 'prune'),
        ]
        for label, color, action in dash_actions:
            btn = self._create_control_button(
                self.dashboard_actions_panel,
                label,
                color,
                lambda a=action: self.run_dashboard_action(a)
            )
            btn.pack(fill=tk.X, expand=False, pady=2, padx=5)

        # Compose action panel
        self.compose_actions_panel = ttk.Frame(individual_actions_frame)
        compose_actions = [
            ('▶️ Up', '#219653', 'up'),
            ('⏹️ Down', '#b80000', 'down'),
            ('🔄 Restart', '#2471a3', 'restart'),
            ('📋 Logs', '#6c757d', 'logs'),
        ]
        for label, color, action in compose_actions:
            btn = self._create_control_button(
                self.compose_actions_panel,
                label,
                color,
                lambda a=action: self.run_compose_action(a)
            )
            btn.pack(fill=tk.X, expand=False, pady=2, padx=5)

        # Info action panel
        self.info_actions_panel = ttk.Frame(individual_actions_frame)
        info_actions = [
            ('🔄 Refresh Info', '#00ADB5', 'refresh'),
            ('📋 Copy to Clipboard', '#6c757d', 'copy'),
        ]
        for label, color, action in info_actions:
            btn = self._create_control_button(
                self.info_actions_panel,
                label,
                color,
                lambda a=action: self.run_info_action(a)
            )
            btn.pack(fill=tk.X, expand=False, pady=2, padx=5)

        # Help action panel
        self.help_actions_panel = ttk.Frame(individual_actions_frame)
        help_actions = [
            ('📚 Overview', '#6c757d', 'overview'),
            ('📦 Containers', '#6c757d', 'containers'),
            ('🌐 Networks', '#6c757d', 'networks'),
            ('🖼️ Images', '#6c757d', 'images'),
            ('💾 Volumes', '#6c757d', 'volumes'),
            ('📊 Dashboard', '#6c757d', 'dashboard'),
            ('🐳 Compose', '#6c757d', 'compose'),
            ('💡 Info Tab', '#6c757d', 'info'),
            ('⚙️ Settings', '#6c757d', 'settings'),
            ('💡 Tips', '#6c757d', 'tips'),
            ('ℹ️ About', '#6c757d', 'about'),
        ]
        for label, color, action in help_actions:
            btn = self._create_control_button(
                self.help_actions_panel,
                label,
                color,
                lambda a=action: self.run_help_action(a)
            )
            btn.pack(fill=tk.X, expand=False, pady=2, padx=5)

        # Settings action panel - Advanced Operations
        self.settings_actions_panel = ttk.Frame(individual_actions_frame)
        
        # Warning label
        warning_label = tk.Label(
            self.settings_actions_panel,
            text="⚠️  Use with caution!",
            font=('Segoe UI', 8, 'italic'),
            fg='#ff6b6b',
            bg=self.FRAME_BG
        )
        warning_label.pack(pady=(5, 10), padx=5)
        
        settings_actions = [
            ('⏹️ Stop All Containers', '#e67e22', self.stop_all_containers),
            ('🗑️ Remove Stopped', '#c0392b', self.remove_all_stopped),
        ]
        for label, color, cmd in settings_actions:
            btn = self._create_control_button(
                self.settings_actions_panel,
                label,
                color,
                cmd
            )
            btn.pack(fill=tk.X, expand=False, pady=2, padx=5)

        # --- Separator ---
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=15, padx=10)

        # Container-only footer: Global actions and application controls
        self.container_footer_panel = ttk.Frame(parent)
        self.container_footer_panel.pack(pady=0, padx=0, fill=tk.X)

        # --- Global Actions Section (container-only) with better icons ---
        ttk.Label(self.container_footer_panel, text="⚡ Global Actions", font=('Segoe UI', 9, 'bold')).pack(pady=(0, 5), padx=10, anchor='w')

        global_actions_frame = ttk.Frame(self.container_footer_panel)
        global_actions_frame.pack(pady=0, padx=10, fill=tk.X)

        # --- Separator ---
        ttk.Separator(self.container_footer_panel, orient='horizontal').pack(fill='x', pady=15, padx=10)

        global_actions = [
            ('▶️ Start All', '#219653', 'start'),
            ('⏹️ Stop All', '#d85000', 'stop'),
            ('⏸️ Pause All', '#d4c100', 'pause'),
            ('▶️ Unpause All', '#00ADB5', 'unpause'),
            ('🔄 Restart All', '#2471a3', 'restart'),
            ('🗑️ Remove All', '#b80000', 'remove')
        ]

        for label, color, action in global_actions:
            btn = tk.Button(
                global_actions_frame,
                text=label,
                bg=color,
                fg='black' if color in ['#d4c100'] else 'white',
                command=lambda a=action: self.run_global_action(a),
                font=('Segoe UI', 9, 'bold'),
                cursor='hand2',
                relief='flat',
                padx=5,
                pady=8,
                width=15
            )
            btn.pack(fill=tk.X, expand=False, pady=2, padx=5)
            btn.bind('<Enter>', lambda e, b=btn: b.config(relief='raised'))
            btn.bind('<Leave>', lambda e, b=btn: b.config(relief='flat'))

        # --- Application Control Section (container-only) with better styling ---
        ttk.Label(self.container_footer_panel, text="🛠️ Application", font=('Segoe UI', 9, 'bold')).pack(pady=(0, 5), padx=10, anchor='w')
        
        app_control_frame = ttk.Frame(self.container_footer_panel)
        app_control_frame.pack(pady=0, padx=10, fill=tk.X)

        refresh_btn = tk.Button(
            app_control_frame, 
            text="🔄 Refresh", 
            bg="#00ADB5", 
            fg='white', 
            command=self.force_refresh_active_tab,
            font=('Segoe UI', 9, 'bold'),
            cursor='hand2',
            relief='flat',
            pady=8,
            width=15
        )
        refresh_btn.pack(fill=tk.X, expand=False, pady=2, padx=5)
        refresh_btn.bind('<Enter>', lambda e: refresh_btn.config(relief='raised'))
        refresh_btn.bind('<Leave>', lambda e: refresh_btn.config(relief='flat'))

        config_btn = tk.Button(
            app_control_frame, 
            text="⚙️ Config", 
            bg="#6c757d", 
            fg='white', 
            command=self.open_config_window,
            font=('Segoe UI', 9, 'bold'),
            cursor='hand2',
            relief='flat',
            pady=8,
            width=15
        )
        config_btn.pack(fill=tk.X, expand=False, pady=2, padx=5)
        config_btn.bind('<Enter>', lambda e: config_btn.config(relief='raised'))
        config_btn.bind('<Leave>', lambda e: config_btn.config(relief='flat'))


    def create_container_widgets(self, parent):
        # Use a Notebook to provide Containers and Network tabs
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.notebook = notebook
        
        # Bind to tab change event
        notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        # --- Containers Tab ---
        containers_tab = ttk.Frame(notebook)
        notebook.add(containers_tab, text='📦 Containers')

        # Add search bar
        search_frame = tk.Frame(containers_tab, bg='#2a3a4a', height=40)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        search_frame.pack_propagate(False)
        
        ttk.Label(search_frame, text="🔍 Search:", font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=5)
        self.container_search_var = tk.StringVar()
        self.container_search_var.trace('w', lambda *args: self.filter_containers())
        search_entry = ttk.Entry(search_frame, textvariable=self.container_search_var, foreground='black')
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        clear_btn = tk.Button(
            search_frame, 
            text="✖", 
            command=lambda: self.container_search_var.set(''),
            bg='#d32f2f',
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            cursor='hand2',
            relief='flat',
            padx=10
        )
        clear_btn.pack(side=tk.LEFT, padx=5)

        tree_frame = ttk.Frame(containers_tab) # A frame to hold the tree and scrollbar
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        cols = ('ID', 'Name', 'Status', 'CPU (%)', 'RAM (%)')
        self.tree = ttk.Treeview(containers_tab, columns=cols, show='headings', selectmode='browse')
        for col in cols:
            self.tree.heading(col, text=col)
            if col == 'ID':
                self.tree.column(col, width=110, anchor=tk.CENTER)  # Fixed width for short ID
            elif col == 'Name':
                self.tree.column(col, width=200, anchor=tk.W)  # Wider for names
            else:
                self.tree.column(col, width=100, anchor=tk.CENTER)

        # Only vertical scrollbar
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar_y.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, in_=tree_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y, in_=tree_frame)

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Double-Button-1>', self.on_container_double_click)
        
        # Enable mouse wheel scrolling - only when mouse is over the tree and content exceeds view
        def _tree_scroll(event):
            if self.tree.yview() != (0.0, 1.0):  # Content exceeds visible area
                self.tree.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"  # Prevent event propagation
        
        def _tree_scroll_linux_up(event):
            if self.tree.yview() != (0.0, 1.0):
                self.tree.yview_scroll(-1, "units")
            return "break"
        
        def _tree_scroll_linux_down(event):
            if self.tree.yview() != (0.0, 1.0):
                self.tree.yview_scroll(1, "units")
            return "break"
        
        self.tree.bind('<MouseWheel>', _tree_scroll)
        self.tree.bind('<Button-4>', _tree_scroll_linux_up)
        self.tree.bind('<Button-5>', _tree_scroll_linux_down)

        # --- Network Tab ---
        network_tab = ttk.Frame(notebook)
        notebook.add(network_tab, text='🌐 Network')

        # Search bar for networks
        net_search_frame = tk.Frame(network_tab, bg='#2a3a4a', height=40)
        net_search_frame.pack(fill=tk.X, padx=5, pady=5)
        net_search_frame.pack_propagate(False)
        
        ttk.Label(net_search_frame, text="🔍 Search:", font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=5)
        self.network_search_var = tk.StringVar()
        self.network_search_var.trace('w', lambda *args: self.filter_networks())
        net_search_entry = ttk.Entry(net_search_frame, textvariable=self.network_search_var, foreground='black')
        net_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        net_clear_btn = tk.Button(
            net_search_frame, 
            text="✖", 
            command=lambda: self.network_search_var.set(''),
            bg='#d32f2f', 
            fg='white', 
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=10
        )
        net_clear_btn.pack(side=tk.LEFT, padx=5)

        net_frame = ttk.Frame(network_tab)
        net_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        net_cols = ('ID', 'Name', 'Driver', 'Scope')
        self.network_tree = ttk.Treeview(network_tab, columns=net_cols, show='headings', selectmode='browse')
        for col in net_cols:
            self.network_tree.heading(col, text=col)
            if col == 'ID':
                self.network_tree.column(col, width=110, anchor=tk.CENTER)  # Fixed width for short ID
            elif col == 'Name':
                self.network_tree.column(col, width=200, anchor=tk.W)  # Wider for names
            else:
                self.network_tree.column(col, width=120, anchor=tk.CENTER)

        # Only vertical scrollbar (no horizontal)
        net_scroll_y = ttk.Scrollbar(net_frame, orient=tk.VERTICAL, command=self.network_tree.yview)
        self.network_tree.configure(yscroll=net_scroll_y.set)

        self.network_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, in_=net_frame)
        net_scroll_y.pack(side=tk.RIGHT, fill=tk.Y, in_=net_frame)

        self.network_tree.bind('<<TreeviewSelect>>', self.on_network_select)
        self.network_tree.bind('<Double-Button-1>', self.on_network_double_click)
        
        # Enable mouse wheel scrolling - only when mouse is over the tree and content exceeds view
        def _net_scroll(event):
            if self.network_tree.yview() != (0.0, 1.0):  # Content exceeds visible area
                self.network_tree.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        def _net_scroll_linux_up(event):
            if self.network_tree.yview() != (0.0, 1.0):
                self.network_tree.yview_scroll(-1, "units")
            return "break"
        
        def _net_scroll_linux_down(event):
            if self.network_tree.yview() != (0.0, 1.0):
                self.network_tree.yview_scroll(1, "units")
            return "break"
        
        self.network_tree.bind('<MouseWheel>', _net_scroll)
        self.network_tree.bind('<Button-4>', _net_scroll_linux_up)
        self.network_tree.bind('<Button-5>', _net_scroll_linux_down)

        # --- Images Tab ---
        images_tab = ttk.Frame(notebook)
        notebook.add(images_tab, text='🖼️ Images')

        # Search bar for images
        img_search_frame = tk.Frame(images_tab, bg='#2a3a4a', height=40)
        img_search_frame.pack(fill=tk.X, padx=5, pady=5)
        img_search_frame.pack_propagate(False)
        
        ttk.Label(img_search_frame, text="🔍 Search:", font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=5)
        self.images_search_var = tk.StringVar()
        self.images_search_var.trace('w', lambda *args: self.filter_images())
        img_search_entry = ttk.Entry(img_search_frame, textvariable=self.images_search_var, foreground='black')
        img_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        img_clear_btn = tk.Button(
            img_search_frame, 
            text="✖", 
            command=lambda: self.images_search_var.set(''),
            bg='#d32f2f', 
            fg='white', 
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=10
        )
        img_clear_btn.pack(side=tk.LEFT, padx=5)

        img_frame = ttk.Frame(images_tab)
        img_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        img_cols = ('ID', 'Repository:Tag', 'Size', 'Created')
        self.images_tree = ttk.Treeview(images_tab, columns=img_cols, show='headings', selectmode='browse')
        for col in img_cols:
            self.images_tree.heading(col, text=col)
            if col == 'ID':
                self.images_tree.column(col, width=110, anchor=tk.CENTER)  # Fixed width for short ID
            elif col == 'Repository:Tag':
                self.images_tree.column(col, width=250, anchor=tk.W)  # Wider for repo:tag
            else:
                self.images_tree.column(col, width=120, anchor=tk.CENTER)

        # Only vertical scrollbar (no horizontal)
        img_scroll_y = ttk.Scrollbar(img_frame, orient=tk.VERTICAL, command=self.images_tree.yview)
        self.images_tree.configure(yscroll=img_scroll_y.set)

        self.images_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, in_=img_frame)
        img_scroll_y.pack(side=tk.RIGHT, fill=tk.Y, in_=img_frame)

        self.images_tree.bind('<<TreeviewSelect>>', self.on_image_select)
        self.images_tree.bind('<Double-Button-1>', self.on_image_double_click)
        
        # Enable mouse wheel scrolling - only when mouse is over the tree and content exceeds view
        def _img_scroll(event):
            if self.images_tree.yview() != (0.0, 1.0):  # Content exceeds visible area
                self.images_tree.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        def _img_scroll_linux_up(event):
            if self.images_tree.yview() != (0.0, 1.0):
                self.images_tree.yview_scroll(-1, "units")
            return "break"
        
        def _img_scroll_linux_down(event):
            if self.images_tree.yview() != (0.0, 1.0):
                self.images_tree.yview_scroll(1, "units")
            return "break"
        
        self.images_tree.bind('<MouseWheel>', _img_scroll)
        self.images_tree.bind('<Button-4>', _img_scroll_linux_up)
        self.images_tree.bind('<Button-5>', _img_scroll_linux_down)

        # --- Volumes Tab ---
        volumes_tab = ttk.Frame(notebook)
        notebook.add(volumes_tab, text='💾 Volumes')

        # Search bar for volumes
        vol_search_frame = tk.Frame(volumes_tab, bg='#2a3a4a', height=40)
        vol_search_frame.pack(fill=tk.X, padx=5, pady=5)
        vol_search_frame.pack_propagate(False)
        
        ttk.Label(vol_search_frame, text="🔍 Search:", font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=5)
        self.volumes_search_var = tk.StringVar()
        self.volumes_search_var.trace('w', lambda *args: self.filter_volumes())
        vol_search_entry = ttk.Entry(vol_search_frame, textvariable=self.volumes_search_var, foreground='black')
        vol_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        vol_clear_btn = tk.Button(
            vol_search_frame, 
            text="✖", 
            command=lambda: self.volumes_search_var.set(''),
            bg='#d32f2f', 
            fg='white', 
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=10
        )
        vol_clear_btn.pack(side=tk.LEFT, padx=5)

        vol_frame = ttk.Frame(volumes_tab)
        vol_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        vol_cols = ('Name', 'Driver', 'Mountpoint', 'Labels')
        self.volumes_tree = ttk.Treeview(volumes_tab, columns=vol_cols, show='headings', selectmode='browse')
        for col in vol_cols:
            self.volumes_tree.heading(col, text=col)
            if col == 'Name':
                self.volumes_tree.column(col, width=180, anchor=tk.W)  # Fixed width for names
            else:
                self.volumes_tree.column(col, width=150, anchor=tk.CENTER)

        # Only vertical scrollbar (no horizontal)
        vol_scroll_y = ttk.Scrollbar(vol_frame, orient=tk.VERTICAL, command=self.volumes_tree.yview)
        self.volumes_tree.configure(yscroll=vol_scroll_y.set)

        self.volumes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, in_=vol_frame)
        vol_scroll_y.pack(side=tk.RIGHT, fill=tk.Y, in_=vol_frame)

        self.volumes_tree.bind('<<TreeviewSelect>>', self.on_volume_select)
        self.volumes_tree.bind('<Double-Button-1>', self.on_volume_double_click)
        
        # Enable mouse wheel scrolling - only when mouse is over the tree and content exceeds view
        def _vol_scroll(event):
            if self.volumes_tree.yview() != (0.0, 1.0):  # Content exceeds visible area
                self.volumes_tree.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        def _vol_scroll_linux_up(event):
            if self.volumes_tree.yview() != (0.0, 1.0):
                self.volumes_tree.yview_scroll(-1, "units")
            return "break"
        
        def _vol_scroll_linux_down(event):
            if self.volumes_tree.yview() != (0.0, 1.0):
                self.volumes_tree.yview_scroll(1, "units")
            return "break"
        
        self.volumes_tree.bind('<MouseWheel>', _vol_scroll)
        self.volumes_tree.bind('<Button-4>', _vol_scroll_linux_up)
        self.volumes_tree.bind('<Button-5>', _vol_scroll_linux_down)

        # --- Dashboard/Overview Tab ---
        dashboard_tab = tk.Frame(notebook, bg='#1e2a35')
        notebook.add(dashboard_tab, text='📊 Dashboard')

        # Create scrollable dashboard
        dash_canvas = tk.Canvas(dashboard_tab, bg='#1e2a35', highlightthickness=0)
        dash_scrollbar = ttk.Scrollbar(dashboard_tab, orient="vertical", command=dash_canvas.yview)
        dash_scrollable_frame = tk.Frame(dash_canvas, bg='#1e2a35')

        dash_scrollable_frame.bind(
            "<Configure>",
            lambda e: dash_canvas.configure(scrollregion=dash_canvas.bbox("all"))
        )

        dash_canvas.create_window((0, 0), window=dash_scrollable_frame, anchor="nw")
        dash_canvas.configure(yscrollcommand=dash_scrollbar.set)

        dash_canvas.pack(side="left", fill="both", expand=True)
        dash_scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling for dashboard - only when content exceeds view
        def _dash_scroll(event):
            if dash_canvas.yview() != (0.0, 1.0):  # Content exceeds visible area
                dash_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        def _dash_scroll_linux_up(event):
            if dash_canvas.yview() != (0.0, 1.0):
                dash_canvas.yview_scroll(-1, "units")
            return "break"
        
        def _dash_scroll_linux_down(event):
            if dash_canvas.yview() != (0.0, 1.0):
                dash_canvas.yview_scroll(1, "units")
            return "break"
        
        # Bind to canvas and all its children recursively
        def bind_dash_to_mousewheel(widget):
            widget.bind('<MouseWheel>', _dash_scroll)
            widget.bind('<Button-4>', _dash_scroll_linux_up)
            widget.bind('<Button-5>', _dash_scroll_linux_down)
            for child in widget.winfo_children():
                bind_dash_to_mousewheel(child)
        
        dash_canvas.bind('<MouseWheel>', _dash_scroll)
        dash_canvas.bind('<Button-4>', _dash_scroll_linux_up)
        dash_canvas.bind('<Button-5>', _dash_scroll_linux_down)

        # Dashboard Content
        dash_content = tk.Frame(dash_scrollable_frame, bg='#1e2a35')
        dash_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title with modern styling
        title_frame = tk.Frame(dash_content, bg='#1e2a35')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        dash_title = tk.Label(title_frame, text="📊 Docker Environment Overview", 
                             font=('Segoe UI', 20, 'bold'), fg='#00ADB5', bg='#1e2a35')
        dash_title.pack(side=tk.LEFT, anchor='w')
        
        # Subtitle
        dash_subtitle = tk.Label(title_frame, text="Real-time monitoring and management", 
                                font=('Segoe UI', 10), fg='#7f8c8d', bg='#1e2a35')
        dash_subtitle.pack(side=tk.LEFT, padx=(15, 0), anchor='w')

        # Statistics Cards Section Label
        stats_label = tk.Label(dash_content, text="📈 Statistics", 
                              font=('Segoe UI', 14, 'bold'), fg='#00ADB5', bg='#1e2a35')
        stats_label.pack(pady=(15, 10), anchor='w')
        
        # Statistics Cards Frame
        cards_frame = tk.Frame(dash_content, bg='#1e2a35')
        cards_frame.pack(fill=tk.X, pady=10)

        # Create stat cards
        self.dash_containers_running = tk.StringVar(value="0")
        self.dash_containers_stopped = tk.StringVar(value="0")
        self.dash_images_count = tk.StringVar(value="0")
        self.dash_volumes_count = tk.StringVar(value="0")
        self.dash_networks_count = tk.StringVar(value="0")

        self._create_stat_card(cards_frame, "� Running Containers", self.dash_containers_running, "#00ff88", 0, 0)
        self._create_stat_card(cards_frame, "⏸️ Stopped Containers", self.dash_containers_stopped, "#ff4444", 0, 1)
        self._create_stat_card(cards_frame, "� Total Images", self.dash_images_count, "#00d4ff", 0, 2)
        self._create_stat_card(cards_frame, "💾 Total Volumes", self.dash_volumes_count, "#ffaa00", 1, 0)
        self._create_stat_card(cards_frame, "🌐 Total Networks", self.dash_networks_count, "#aa88ff", 1, 1)

        # Separator
        separator1 = tk.Frame(dash_content, bg='#34495e', height=2)
        separator1.pack(fill=tk.X, pady=(30, 0))
        
        # Quick Actions Section
        actions_label = tk.Label(dash_content, text="⚡ Quick Actions", 
                                font=('Segoe UI', 14, 'bold'), fg='#00ADB5', bg='#1e2a35')
        actions_label.pack(pady=(30, 15), anchor='w')

        quick_actions_frame = tk.Frame(dash_content, bg='#1e2a35')
        quick_actions_frame.pack(fill=tk.X, pady=5)

        quick_actions = [
            ("🔄 Refresh All", self.refresh_dashboard, "#00ADB5"),
            ("🗑️ Prune System", self.prune_system, "#d32f2f"),
            ("📊 System Info", self.show_system_info, "#6c757d")
        ]

        for text, command, color in quick_actions:
            # Create a card-style button container
            btn_container = tk.Frame(quick_actions_frame, bg='#2a3f54', relief='flat', 
                                    bd=0, highlightthickness=2, highlightbackground=color)
            btn_container.pack(side=tk.LEFT, padx=10, pady=5)
            
            btn = tk.Button(
                btn_container,
                text=text,
                bg='#2a3f54',
                fg='white',
                font=('Segoe UI', 11, 'bold'),
                command=command,
                relief='flat',
                width=18,
                height=2,
                anchor='center',
                cursor='hand2',
                activebackground='#34495e',
                activeforeground='white'
            )
            btn.pack(padx=3, pady=3)
            
            # Add hover effect to both container and button
            def on_enter(e, cont=btn_container, b=btn, c=color):
                cont.config(highlightthickness=3, bg='#34495e')
                b.config(bg='#34495e')
            
            def on_leave(e, cont=btn_container, b=btn, c=color):
                cont.config(highlightthickness=2, bg='#2a3f54')
                b.config(bg='#2a3f54')
            
            btn.bind('<Enter>', on_enter)
            btn.bind('<Leave>', on_leave)
            btn_container.bind('<Enter>', on_enter)
            btn_container.bind('<Leave>', on_leave)

        # Now bind mouse wheel to all widgets in dashboard
        bind_dash_to_mousewheel(dash_scrollable_frame)

        # Start dashboard updates
        self.after(1000, self.update_dashboard)

        # --- Docker Settings Tab ---
        settings_tab = tk.Frame(notebook, bg='#1e2a35')
        notebook.add(settings_tab, text='⚙️ Settings')

        # Create scrollable settings content
        settings_canvas = tk.Canvas(settings_tab, bg='#1e2a35', highlightthickness=0)
        settings_scrollbar = ttk.Scrollbar(settings_tab, orient="vertical", command=settings_canvas.yview)
        settings_scrollable_frame = tk.Frame(settings_canvas, bg='#1e2a35')

        settings_scrollable_frame.bind(
            "<Configure>",
            lambda e: settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))
        )

        settings_canvas.create_window((0, 0), window=settings_scrollable_frame, anchor="nw")
        settings_canvas.configure(yscrollcommand=settings_scrollbar.set)

        settings_canvas.pack(side="left", fill="both", expand=True)
        settings_scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel scrolling for settings
        def _settings_scroll(event):
            if settings_canvas.yview() != (0.0, 1.0):
                settings_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        def _settings_scroll_linux_up(event):
            if settings_canvas.yview() != (0.0, 1.0):
                settings_canvas.yview_scroll(-1, "units")
            return "break"
        
        def _settings_scroll_linux_down(event):
            if settings_canvas.yview() != (0.0, 1.0):
                settings_canvas.yview_scroll(1, "units")
            return "break"
        
        settings_canvas.bind('<MouseWheel>', _settings_scroll)
        settings_canvas.bind('<Button-4>', _settings_scroll_linux_up)
        settings_canvas.bind('<Button-5>', _settings_scroll_linux_down)

        # Recursive function to bind mousewheel to all child widgets
        def bind_settings_to_mousewheel(widget):
            widget.bind('<MouseWheel>', _settings_scroll)
            widget.bind('<Button-4>', _settings_scroll_linux_up)
            widget.bind('<Button-5>', _settings_scroll_linux_down)
            for child in widget.winfo_children():
                bind_settings_to_mousewheel(child)

        # Settings header
        settings_header_frame = tk.Frame(settings_scrollable_frame, bg='#1e2a35')
        settings_header_frame.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        settings_header = tk.Label(settings_header_frame, text="⚙️ Docker System Settings", 
                                 font=('Segoe UI', 16, 'bold'), fg='#00d4ff', bg='#1e2a35')
        settings_header.pack(side=tk.LEFT)
        
        settings_subtitle = tk.Label(settings_header_frame, text="  Configure and manage Docker", 
                                   font=('Segoe UI', 9, 'italic'), fg='#888888', bg='#1e2a35')
        settings_subtitle.pack(side=tk.LEFT, padx=8)

        # === Main Container (2 columns) ===
        main_container = tk.Frame(settings_scrollable_frame, bg='#1e2a35')
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # Left Column
        left_column = tk.Frame(main_container, bg='#1e2a35')
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        
        # Right Column
        right_column = tk.Frame(main_container, bg='#1e2a35')
        right_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        # === LEFT COLUMN ===
        
        # Quick Control Panel
        control_card = tk.Frame(left_column, bg='#2a3a4a', relief='flat')
        control_card.pack(fill=tk.X, pady=(0, 8))
        
        control_inner = tk.Frame(control_card, bg='#2a3a4a')
        control_inner.pack(fill=tk.X, padx=10, pady=10)
        
        control_label = tk.Label(control_inner, text="🎮 Quick Control Panel", 
                                font=('Segoe UI', 11, 'bold'), fg='#00d4ff', bg='#2a3a4a')
        control_label.pack(anchor='w', pady=(0, 5))
        
        # Row 1: Auto-refresh toggle
        refresh_row = tk.Frame(control_inner, bg='#2a3a4a')
        refresh_row.pack(fill=tk.X, pady=2)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_check = tk.Checkbutton(refresh_row, text='🔄 Auto-refresh enabled', 
                                           variable=self.auto_refresh_var,
                                           command=self.toggle_auto_refresh,
                                           bg='#2a3a4a', fg='#e0e0e0', 
                                           selectcolor='#1e2a35', activebackground='#2a3a4a',
                                           font=('Segoe UI', 9), cursor='hand2')
        auto_refresh_check.pack(side=tk.LEFT)
        
        # Row 2: Refresh interval
        interval_row = tk.Frame(control_inner, bg='#2a3a4a')
        interval_row.pack(fill=tk.X, pady=2)
        
        tk.Label(interval_row, text='⏱️ Refresh interval:', bg='#2a3a4a', fg='#cccccc',
                font=('Segoe UI', 9)).pack(side=tk.LEFT)
        
        self.refresh_interval_var = tk.StringVar(value='5')
        interval_spinbox = tk.Spinbox(interval_row, from_=1, to=60, width=5,
                                      textvariable=self.refresh_interval_var,
                                      bg='#ffffff', fg='#000000', font=('Segoe UI', 9),
                                      command=self.update_refresh_interval)
        interval_spinbox.pack(side=tk.LEFT, padx=8)
        
        tk.Label(interval_row, text='seconds', bg='#2a3a4a', fg='#888888',
                font=('Segoe UI', 9)).pack(side=tk.LEFT)
        
        # Row 3: Log level
        log_level_row = tk.Frame(control_inner, bg='#2a3a4a')
        log_level_row.pack(fill=tk.X, pady=2)
        
        tk.Label(log_level_row, text='📝 Log level:', bg='#2a3a4a', fg='#cccccc',
                font=('Segoe UI', 9)).pack(side=tk.LEFT)
        
        self.log_level_var = tk.StringVar(value='INFO')
        log_combo = ttk.Combobox(log_level_row, textvariable=self.log_level_var,
                                values=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                                width=10, state='readonly')
        log_combo.pack(side=tk.LEFT, padx=8)
        
        # Row 4: Theme toggle
        theme_row = tk.Frame(control_inner, bg='#2a3a4a')
        theme_row.pack(fill=tk.X, pady=2)
        
        self.dark_mode_var = tk.BooleanVar(value=True)
        theme_check = tk.Checkbutton(theme_row, text='🌙 Dark mode', 
                                    variable=self.dark_mode_var,
                                    bg='#2a3a4a', fg='#e0e0e0', 
                                    selectcolor='#1e2a35', activebackground='#2a3a4a',
                                    font=('Segoe UI', 9), cursor='hand2')
        theme_check.pack(side=tk.LEFT)

        # System Cleanup Card
        cleanup_card = tk.Frame(left_column, bg='#2a3a4a', relief='flat')
        cleanup_card.pack(fill=tk.X, pady=(0, 8))
        
        cleanup_inner = tk.Frame(cleanup_card, bg='#2a3a4a')
        cleanup_inner.pack(fill=tk.X, padx=10, pady=10)
        
        cleanup_label = tk.Label(cleanup_inner, text="🧹 System Cleanup", 
                                font=('Segoe UI', 11, 'bold'), fg='#ff6b6b', bg='#2a3a4a')
        cleanup_label.pack(anchor='w', pady=(0, 3))
        
        cleanup_desc = tk.Label(cleanup_inner, text="Remove unused resources", 
                              font=('Segoe UI', 8), fg='#999999', bg='#2a3a4a')
        cleanup_desc.pack(anchor='w', pady=(0, 10))
        
        cleanup_btns = [
            ('🗑️ Prune All', '#dc3545', self.prune_system),
            ('📦 Containers', '#ff6b6b', self.prune_containers),
            ('🖼️ Images', '#ff8c42', self.prune_images),
            ('🔗 Networks', '#ffa94d', self.prune_networks),
            ('💾 Volumes', '#ffb347', self.prune_volumes),
        ]
        
        for i, (text, color, cmd) in enumerate(cleanup_btns):
            btn = tk.Button(cleanup_inner, text=text, bg=color, fg='white',
                          font=('Segoe UI', 8, 'bold'), command=cmd, relief='flat', 
                          padx=10, pady=6, cursor='hand2')
            if i == 0:
                btn.pack(fill=tk.X, pady=(0, 5))
            else:
                btn.pack(side=tk.LEFT, padx=(0, 5) if i < len(cleanup_btns)-1 else 0, expand=True, fill=tk.X)

        # Resource Limits Card
        limits_card = tk.Frame(left_column, bg='#2a3a4a', relief='flat')
        limits_card.pack(fill=tk.X, pady=(0, 8))
        
        limits_inner = tk.Frame(limits_card, bg='#2a3a4a')
        limits_inner.pack(fill=tk.X, padx=10, pady=10)
        
        limits_label = tk.Label(limits_inner, text="📊 Default Resource Limits", 
                               font=('Segoe UI', 11, 'bold'), fg='#4ecdc4', bg='#2a3a4a')
        limits_label.pack(anchor='w', pady=(0, 5))
        
        # Memory limit
        mem_row = tk.Frame(limits_inner, bg='#2a3a4a')
        mem_row.pack(fill=tk.X, pady=3)
        tk.Label(mem_row, text='💾 Memory limit:', bg='#2a3a4a', fg='#cccccc',
                font=('Segoe UI', 9), width=15, anchor='w').pack(side=tk.LEFT)
        self.mem_limit_var = tk.StringVar(value='512m')
        mem_entry = tk.Entry(mem_row, textvariable=self.mem_limit_var, width=12,
                            bg='#ffffff', fg='#000000', font=('Segoe UI', 9))
        mem_entry.pack(side=tk.LEFT, padx=5)
        
        # CPU limit
        cpu_row = tk.Frame(limits_inner, bg='#2a3a4a')
        cpu_row.pack(fill=tk.X, pady=3)
        tk.Label(cpu_row, text='⚡ CPU limit:', bg='#2a3a4a', fg='#cccccc',
                font=('Segoe UI', 9), width=15, anchor='w').pack(side=tk.LEFT)
        self.cpu_limit_var = tk.StringVar(value='1.0')
        cpu_entry = tk.Entry(cpu_row, textvariable=self.cpu_limit_var, width=12,
                            bg='#ffffff', fg='#000000', font=('Segoe UI', 9))
        cpu_entry.pack(side=tk.LEFT, padx=5)
        
        apply_limits_btn = tk.Button(limits_inner, text='✓ Apply Changes', 
                                     bg='#4ecdc4', fg='white', font=('Segoe UI', 9, 'bold'),
                                     relief='flat', cursor='hand2', padx=15, pady=6,
                                     command=self.apply_default_limits)
        apply_limits_btn.pack(pady=(8, 0))

        # Export System Report Card
        export_card = tk.Frame(left_column, bg='#2a3a4a', relief='flat')
        export_card.pack(fill=tk.X, pady=(0, 8))
        
        export_inner = tk.Frame(export_card, bg='#2a3a4a')
        export_inner.pack(fill=tk.X, padx=10, pady=10)
        
        export_label = tk.Label(export_inner, text="📄 Export System Report", 
                               font=('Segoe UI', 11, 'bold'), fg='#ffd93d', bg='#2a3a4a')
        export_label.pack(anchor='w', pady=(0, 3))
        
        export_desc = tk.Label(export_inner, text="Save complete system snapshot", 
                              font=('Segoe UI', 8), fg='#999999', bg='#2a3a4a')
        export_desc.pack(anchor='w', pady=(0, 10))
        
        export_btn = tk.Button(export_inner, text='💾 Export Full Report', 
                              bg='#ffd93d', fg='#1e1e1e', font=('Segoe UI', 9, 'bold'),
                              relief='flat', cursor='hand2', padx=15, pady=8,
                              command=self.export_system_report)
        export_btn.pack(fill=tk.X)
        
        export_note = tk.Label(export_inner, 
                              text="Includes: logs, containers, images, networks, volumes,\nsystem info, disk usage, and settings", 
                              font=('Segoe UI', 7), fg='#777777', bg='#2a3a4a', justify=tk.LEFT)
        export_note.pack(anchor='w', pady=(5, 0))

        # === RIGHT COLUMN ===
        
        # System Information Card
        info_card = tk.Frame(right_column, bg='#2a3a4a', relief='flat')
        info_card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        info_inner = tk.Frame(info_card, bg='#2a3a4a')
        info_inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        info_header = tk.Frame(info_inner, bg='#2a3a4a')
        info_header.pack(fill=tk.X)
        
        info_label = tk.Label(info_header, text="📊 System Information", 
                            font=('Segoe UI', 11, 'bold'), fg='#4ecdc4', bg='#2a3a4a')
        info_label.pack(side=tk.LEFT)
        
        refresh_info_btn = tk.Button(info_header, text='🔄 Refresh', 
                                     command=self.refresh_docker_info,
                                     bg='#4ecdc4', fg='white', font=('Segoe UI', 8, 'bold'),
                                     relief='flat', cursor='hand2', padx=10, pady=4)
        refresh_info_btn.pack(side=tk.RIGHT)
        
        self.docker_info_text = scrolledtext.ScrolledText(
            info_inner, height=14, wrap=tk.WORD,
            bg="#1e1e1e", fg="#00ff99", font=("Consolas", 8),
            relief='flat', borderwidth=0, insertbackground='#00ff99'
        )
        self.docker_info_text.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        # Disk Usage Card
        disk_card = tk.Frame(right_column, bg='#2a3a4a', relief='flat')
        disk_card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        disk_inner = tk.Frame(disk_card, bg='#2a3a4a')
        disk_inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        disk_header = tk.Frame(disk_inner, bg='#2a3a4a')
        disk_header.pack(fill=tk.X)
        
        disk_label = tk.Label(disk_header, text="💽 Disk Usage", 
                            font=('Segoe UI', 11, 'bold'), fg='#95e1d3', bg='#2a3a4a')
        disk_label.pack(side=tk.LEFT)
        
        refresh_disk_btn = tk.Button(disk_header, text='📊 Check', 
                                     command=self.check_disk_usage,
                                     bg='#95e1d3', fg='#1e1e1e', font=('Segoe UI', 8, 'bold'),
                                     relief='flat', cursor='hand2', padx=10, pady=4)
        refresh_disk_btn.pack(side=tk.RIGHT)
        
        self.disk_usage_text = scrolledtext.ScrolledText(
            disk_inner, height=10, wrap=tk.WORD,
            bg="#1e1e1e", fg="#95e1d3", font=("Consolas", 8),
            relief='flat', borderwidth=0, insertbackground='#95e1d3'
        )
        self.disk_usage_text.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        # Bind mousewheel to all widgets in settings
        bind_settings_to_mousewheel(settings_scrollable_frame)

        # Load initial data for Settings tab
        self.after(500, self.refresh_docker_info)
        self.after(1000, self.check_disk_usage)

        # --- Info Tab ---
        info_tab = tk.Frame(notebook, bg='#1e2a35')
        notebook.add(info_tab, text='💡 Info')

        # Info tab displays detailed information about selected items
        self.info_placeholder_label = tk.Label(info_tab, text='Select an item from any tab to view detailed information', 
                             font=('Segoe UI', 10, 'italic'), foreground='#00d4ff', bg='#1e2a35')
        self.info_placeholder_label.pack(pady=20)

        # Create a scrolled text widget for displaying detailed info
        self.info_text = scrolledtext.ScrolledText(
            info_tab, 
            state='disabled', 
            wrap=tk.WORD, 
            bg="#1e2a35", 
            fg="#e0e0e0", 
            font=("Consolas", 10),
            relief='flat',
            borderwidth=2,
            padx=10,
            pady=10,
            insertbackground='#00d4ff'
        )
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure text tags for better formatting (dark theme colors)
        self.info_text.tag_configure('title', font=('Segoe UI', 14, 'bold'), foreground='#00d4ff')
        self.info_text.tag_configure('section', font=('Segoe UI', 11, 'bold'), foreground='#00ff88')
        self.info_text.tag_configure('key', font=('Consolas', 10, 'bold'), foreground='#00d4ff')
        self.info_text.tag_configure('value', font=('Consolas', 10), foreground='#cccccc')
        self.info_text.tag_configure('warning', font=('Consolas', 10), foreground='#ff4444')

        # Store current selection context
        self.current_info_context = {'type': None, 'id': None}

        # --- Help Tab ---
        help_tab = tk.Frame(notebook, bg='#1e2a35')
        notebook.add(help_tab, text='📚 Help')

        # Create a canvas with scrollbar for help content
        help_canvas = tk.Canvas(help_tab, bg='#1e2a35', highlightthickness=0)
        help_scrollbar = ttk.Scrollbar(help_tab, orient="vertical", command=help_canvas.yview)
        help_scrollable_frame = tk.Frame(help_canvas, bg='#1e2a35')
        
        # Store reference for later use
        self.help_canvas = help_canvas

        help_scrollable_frame.bind(
            "<Configure>",
            lambda e: help_canvas.configure(scrollregion=help_canvas.bbox("all"))
        )

        help_canvas.create_window((0, 0), window=help_scrollable_frame, anchor="nw")
        help_canvas.configure(yscrollcommand=help_scrollbar.set)

        help_canvas.pack(side="left", fill="both", expand=True)
        help_scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling for help - only when content exceeds view
        def _help_scroll(event):
            if help_canvas.yview() != (0.0, 1.0):  # Content exceeds visible area
                help_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        def _help_scroll_linux_up(event):
            if help_canvas.yview() != (0.0, 1.0):
                help_canvas.yview_scroll(-1, "units")
            return "break"
        
        def _help_scroll_linux_down(event):
            if help_canvas.yview() != (0.0, 1.0):
                help_canvas.yview_scroll(1, "units")
            return "break"
        
        # Bind to canvas and all its children recursively
        def bind_to_mousewheel(widget):
            widget.bind('<MouseWheel>', _help_scroll)
            widget.bind('<Button-4>', _help_scroll_linux_up)
            widget.bind('<Button-5>', _help_scroll_linux_down)
            for child in widget.winfo_children():
                bind_to_mousewheel(child)
        
        help_canvas.bind('<MouseWheel>', _help_scroll)
        help_canvas.bind('<Button-4>', _help_scroll_linux_up)
        help_canvas.bind('<Button-5>', _help_scroll_linux_down)

        # Help content
        help_content = tk.Frame(help_scrollable_frame, bg='#1e2a35')
        help_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Dictionary to store help section positions
        self.help_sections = {}

        # Title
        title_label = tk.Label(help_content, text="📚 Docker Monitor Manager - User Guide", 
                               font=('Segoe UI', 18, 'bold'), fg='#00d4ff', bg='#1e2a35')
        title_label.pack(pady=(0, 20), anchor='w')

        # Add help sections with bookmarks
        self.help_sections['overview'] = self._add_help_section(help_content, "🎯 Overview", 
            "Docker Monitor Manager is a comprehensive GUI application for managing Docker containers, networks, "
            "images, and volumes. It provides real-time monitoring, control actions, and detailed information "
            "about your Docker environment.")

        self.help_sections['containers'] = self._add_help_section(help_content, "📦 Containers Tab", 
            "View all your Docker containers with real-time statistics:\n\n"
            "• Container list shows: ID, Name, Status, CPU%, RAM%, and Clones count\n"
            "• Select a container to see available actions in the left panel\n"
            "• Available actions:\n"
            "  - Start/Stop/Restart: Control container lifecycle\n"
            "  - Remove: Delete the container\n"
            "  - Inspect: View detailed container information\n"
            "  - Pause/Unpause: Suspend/resume container processes\n"
            "  - Clone: Create a duplicate of the container\n\n"
            "Global Actions (bottom of control panel):\n"
            "  - Remove All: Delete all stopped containers\n"
            "  - Stop All: Stop all running containers\n"
            "  - Start All: Start all stopped containers")

        self.help_sections['networks'] = self._add_help_section(help_content, "🌐 Network Tab", 
            "Manage Docker networks:\n\n"
            "• View all networks with ID, Name, Driver, and Scope\n"
            "• Select a network to perform actions:\n"
            "  - Inspect: View network details\n"
            "  - Remove: Delete the network\n"
            "  - Create: Create a new network\n"
            "  - Connect: Connect a container to the network\n"
            "  - Disconnect: Remove a container from the network\n"
            "  - Prune: Remove all unused networks")

        self.help_sections['images'] = self._add_help_section(help_content, "🖼️ Images Tab", 
            "Manage Docker images:\n\n"
            "• View all images with ID, Repository:Tag, Size, and Created date\n"
            "• Select an image to perform actions:\n"
            "  - Inspect: View image details and layers\n"
            "  - Remove: Delete the image\n"
            "  - Pull: Pull a new image from Docker registry\n\n"
            "Tip: Select an image to see which containers are using it in the Info tab")

        self.help_sections['volumes'] = self._add_help_section(help_content, "💾 Volumes Tab", 
            "Manage Docker volumes:\n\n"
            "• View all volumes with Name, Driver, Mountpoint, and Labels\n"
            "• Select a volume to perform actions:\n"
            "  - Inspect: View volume details\n"
            "  - Remove: Delete the volume (warning: data will be lost)\n"
            "  - Prune: Remove all unused volumes\n\n"
            "Tip: Check the Info tab to see which containers are using a volume")

        self.help_sections['dashboard'] = self._add_help_section(help_content, "📊 Dashboard Tab", 
            "System overview and quick actions:\n\n"
            "Statistics Cards:\n"
            "  - Running Containers: Number of currently running containers\n"
            "  - Stopped Containers: Number of stopped containers\n"
            "  - Images: Total Docker images on your system\n"
            "  - Volumes: Total Docker volumes\n"
            "  - Networks: Total Docker networks\n\n"
            "Quick Actions:\n"
            "  - Refresh All: Update all dashboard statistics\n"
            "  - Prune System: Clean up unused Docker objects (images, containers, networks, volumes)\n"
            "  - System Info: Display detailed Docker system information\n\n"
            "Tip: Use this tab for a quick overview of your Docker environment. All operations are logged in the main application log.")

        self.help_sections['compose'] = self._add_help_section(help_content, "🐳 Compose Tab", 
            "Docker Compose project management:\n\n"
            "Project Setup:\n"
            "  - Browse or enter the path to your docker-compose project directory\n"
            "  - The docker-compose.yml file will be automatically loaded and displayed\n\n"
            "Available Actions:\n"
            "  - ▶️ Up: Start the compose project (docker-compose up -d)\n"
            "  - ⏹️ Down: Stop and remove compose project containers\n"
            "  - 🔄 Restart: Restart the compose project\n"
            "  - 📋 Logs: View logs from all compose services\n"
            "  - 📝 PS: List all containers in the compose project\n\n"
            "Compose File Viewer:\n"
            "  - View the contents of your docker-compose.yml\n"
            "  - Edit the file directly in the application\n\n"
            "Output Panel:\n"
            "  - Shows command output and errors\n"
            "  - Helps debug compose issues\n\n"
            "Tip: Great for managing multi-container applications defined in compose files")

        self.help_sections['info'] = self._add_help_section(help_content, "💡 Info Tab", 
            "View detailed information about selected items:\n\n"
            "• Select any container, network, image, or volume from other tabs\n"
            "• Switch to the Info tab to see comprehensive details\n"
            "• Information includes:\n"
            "  - For Containers: networks, ports, volumes, environment, resources\n"
            "  - For Networks: IPAM config, connected containers, options\n"
            "  - For Images: size, configuration, containers using it\n"
            "  - For Volumes: mountpoint, containers using it, labels\n\n"
            "This tab helps you understand relationships between Docker objects")

        self.help_sections['settings'] = self._add_help_section(help_content, "⚙️ Configuration & Settings", 
            "Access configuration from the Controls panel:\n\n"
            "• Click 'Edit Config' to modify monitoring thresholds\n"
            "• Set CPU limit, RAM limit, and clone limits\n"
            "• Settings are saved to config file for persistence")

        self.help_sections['tips'] = self._add_help_section(help_content, "💡 Tips & Best Practices", 
            "• Always check the Info tab before removing containers/networks/volumes\n"
            "• Monitor the Application Logs panel for operation status\n"
            "• Use 'Inspect' before 'Remove' to verify what you're deleting\n"
            "• The Docker Terminal is useful for commands not in the GUI\n"
            "• Container statistics update automatically every few seconds\n"
            "• Double-click any item to copy its ID to clipboard")

        # About Section
        ttk.Separator(help_content, orient='horizontal').pack(fill='x', pady=20)
        
        about_frame = tk.Frame(help_content, bg='#1e2a35')
        about_frame.pack(fill=tk.X, pady=10)
        
        # Store reference to about section (use frame instead of label for better positioning)
        self.help_sections['about'] = about_frame

        about_title = tk.Label(about_frame, text="ℹ️ About", 
                              font=('Segoe UI', 16, 'bold'), fg='#00d4ff', bg='#1e2a35')
        about_title.pack(anchor='w', pady=(0, 10))

        about_text = tk.Label(about_frame, 
                             text="Docker Monitor Manager v1.0\n\n"
                                  "A comprehensive Docker management and monitoring tool\n"
                                  "built with Python and tkinter.\n\n",
                             font=('Segoe UI', 10), fg='#e0e0e0', bg='#1e2a35', justify='left')
        about_text.pack(anchor='w')

        # Developer info
        dev_frame = tk.Frame(about_frame, bg='#1e2a35')
        dev_frame.pack(fill=tk.X, pady=10)

        dev_label = tk.Label(dev_frame, text="👨‍💻 Developer:", 
                            font=('Segoe UI', 11, 'bold'), fg='#e0e0e0', bg='#1e2a35')
        dev_label.pack(anchor='w')

        # Email
        email_frame = tk.Frame(dev_frame, bg='#1e2a35')
        email_frame.pack(fill=tk.X, pady=5)
        
        email_icon = tk.Label(email_frame, text="📧 Email:", 
                             font=('Segoe UI', 10), fg='#aaaaaa', bg='#1e2a35')
        email_icon.pack(side=tk.LEFT)
        
        email_link = tk.Label(email_frame, text="amirkhoshdellouyeh@gmail.com", 
                             font=('Segoe UI', 10, 'underline'), fg='#00d4ff', bg='#1e2a35', cursor='hand2')
        email_link.pack(side=tk.LEFT, padx=5)
        email_link.bind("<Button-1>", lambda e: self._open_email())

        # GitHub
        github_frame = tk.Frame(dev_frame, bg='#1e2a35')
        github_frame.pack(fill=tk.X, pady=5)
        
        github_icon = tk.Label(github_frame, text="🔗 GitHub:", 
                              font=('Segoe UI', 10), fg='#aaaaaa', bg='#1e2a35')
        github_icon.pack(side=tk.LEFT)
        
        github_link = tk.Label(github_frame, text="https://github.com/amir-khoshdel-louyeh", 
                              font=('Segoe UI', 10, 'underline'), fg='#00d4ff', bg='#1e2a35', cursor='hand2')
        github_link.pack(side=tk.LEFT, padx=5)
        github_link.bind("<Button-1>", lambda e: self._open_github())

        # License
        license_text = tk.Label(dev_frame, 
                               text="\n© 2025 Amir Khoshdel Louyeh. All rights reserved.\n"
                                    "This software is provided as-is without warranty.",
                               font=('Segoe UI', 9, 'italic'), fg='#888888', bg='#1e2a35', justify='left')
        license_text.pack(anchor='w', pady=(10, 0))
        
        # Now bind mouse wheel to all widgets in help tab
        bind_to_mousewheel(help_scrollable_frame)

    def _add_help_section(self, parent, title, content):
        """Wrapper for UIComponents.add_help_section for backward compatibility."""
        return UIComponents.add_help_section(parent, title, content)


    def _open_email(self):
        """Open default email client with developer's email."""
        import webbrowser
        webbrowser.open("mailto:amirkhoshdellouyeh@gmail.com")

    def _open_github(self):
        """Open GitHub profile in default browser."""
        import webbrowser
        webbrowser.open("https://github.com/amir-khoshdel-louyeh")

    # --- Dashboard Tab Methods ---
    def _create_stat_card(self, parent, label, var, color, row, col):
        """Wrapper for UIComponents.create_stat_card for backward compatibility."""
        UIComponents.create_stat_card(parent, label, var, color, row, col)


    def update_dashboard(self):
        """Update dashboard statistics."""
        dash_vars = {
            'running': self.dash_containers_running,
            'stopped': self.dash_containers_stopped,
            'images': self.dash_images_count,
            'volumes': self.dash_volumes_count,
            'networks': self.dash_networks_count
        }
        SystemManager.update_dashboard(dash_vars)
        self.after(5000, self.update_dashboard)

    def refresh_dashboard(self):
        """Manually refresh dashboard."""
        self.update_dashboard()
        logging.info("📊 Dashboard refreshed manually")

    def prune_system(self):
        """Prune unused Docker objects."""
        SystemManager.prune_system(self.status_bar, self.refresh_all_tabs)

    def show_system_info(self):
        """Show Docker system information."""
        SystemManager.show_system_info(self)

    # --- Settings Tab Methods ---
    def export_system_report(self):
        """Export complete system report to a text file."""
        SystemManager.export_system_report(
            self, self.status_bar,
            default_mem_limit=getattr(self, 'default_mem_limit', None),
            default_cpu_limit=getattr(self, 'default_cpu_limit', None),
            auto_refresh_enabled=hasattr(self, 'auto_refresh_var') and self.auto_refresh_var.get(),
            refresh_interval=self.refresh_interval_var.get() if hasattr(self, 'refresh_interval_var') else None
        )
    
    def apply_default_limits(self):
        """Apply default resource limits."""
        try:
            mem_limit = self.mem_limit_var.get().strip()
            cpu_limit = self.cpu_limit_var.get().strip()
            
            # Validate memory limit format (e.g., 512m, 1g, 2048m)
            if not mem_limit or not any(mem_limit.endswith(suffix) for suffix in ['m', 'M', 'g', 'G', 'k', 'K']):
                messagebox.showerror('Error', 'Invalid memory limit format!\n\nExamples: 512m, 1g, 2048m')
                return
            
            # Validate CPU limit (should be a number)
            try:
                cpu_val = float(cpu_limit)
                if cpu_val <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror('Error', 'Invalid CPU limit!\n\nMust be a positive number (e.g., 1.0, 2.5)')
                return
            
            # Store the values as instance variables
            self.default_mem_limit = mem_limit
            self.default_cpu_limit = cpu_limit
            
            logging.info(f"✓ Default limits set: Memory={mem_limit}, CPU={cpu_limit}")
            messagebox.showinfo('Success', 
                f'Default resource limits applied:\n\n'
                f'💾 Memory: {mem_limit}\n'
                f'⚡ CPU: {cpu_limit}\n\n'
                f'These limits will be used when creating new containers.')
            self.status_bar.config(text=f"✓ Default limits: Mem={mem_limit}, CPU={cpu_limit}")
            
        except Exception as e:
            logging.error(f"Failed to apply default limits: {e}")
            messagebox.showerror('Error', f'Failed to apply limits: {e}')

    # --- Compose Tab Methods ---
    def toggle_auto_refresh(self):
        """Toggle auto-refresh on/off."""
        if self.auto_refresh_var.get():
            logging.info("✓ Auto-refresh enabled")
            self.status_bar.config(text="🔄 Auto-refresh enabled")
        else:
            logging.info("⏸️ Auto-refresh disabled")
            self.status_bar.config(text="⏸️ Auto-refresh disabled")

    def update_refresh_interval(self):
        """Update refresh interval."""
        interval = self.refresh_interval_var.get()
        logging.info(f"⏱️ Refresh interval set to {interval} seconds")
        self.status_bar.config(text=f"⏱️ Refresh interval: {interval}s")

    def prune_containers(self):
        """Remove all stopped containers."""
        PruneManager.prune_containers(self.status_bar, self.refresh_all_tabs)

    def prune_images(self):
        """Remove unused images."""
        PruneManager.prune_images(self.status_bar, self.refresh_all_tabs)

    def prune_networks(self):
        """Remove unused networks."""
        PruneManager.prune_networks(self.status_bar, self.refresh_all_tabs)

    def prune_volumes(self):
        """Remove unused volumes."""
        VolumeManager.prune_volumes(self.refresh_all_tabs, self.status_bar)

    def refresh_docker_info(self):
        """Refresh Docker system information."""
        SystemManager.refresh_docker_info(self.docker_info_text, self.status_bar)

    def _update_docker_info_text(self, text):
        """Update Docker info text widget."""
        InfoDisplayManager.update_text_widget(self.docker_info_text, text)

    def check_disk_usage(self):
        """Check Docker disk usage."""
        SystemManager.check_disk_usage(self.disk_usage_text, self.status_bar)

    def _update_disk_usage_text(self, text):
        """Update disk usage text widget."""
        InfoDisplayManager.update_text_widget(self.disk_usage_text, text)

    def stop_all_containers(self):
        """Stop all running containers."""
        def status_callback(text):
            self.status_bar.config(text=text)
        
        def log_callback(func):
            self.after(0, func)
        
        ContainerManager.stop_all_containers(status_callback, log_callback)
        self.after(500, self.refresh_all_tabs)

    def remove_all_stopped(self):
        """Remove all stopped containers."""
        PruneManager.remove_all_stopped_containers(self.status_bar, self.refresh_all_tabs)

    def refresh_all_tabs(self):
        """Refresh all tabs."""
        try:
            # Refresh containers
            self.force_refresh_containers()
            # Refresh networks
            threading.Thread(target=self._fetch_networks_for_refresh, daemon=True).start()
            # Refresh images and volumes directly
            self.update_images_list()
            self.update_volumes_list()
        except Exception as e:
            logging.error(f"Error refreshing tabs: {e}")

    def create_log_widgets(self, parent):
        self.log_text = scrolledtext.ScrolledText(parent, state='disabled', wrap=tk.WORD, bg="#1e1e1e", fg="#00ff99", font=("Consolas", 9), relief='flat', borderwidth=2)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_terminal_widgets(self, parent):
        # Use the new DockerTerminal widget (queue-based)
        self.docker_terminal_widget = DockerTerminal(
            parent,
            bg="#1e1e1e", fg="#f1f1f1",
            font=("Consolas", 10), relief='flat', borderwidth=2,
            insertbackground=self.FG_COLOR
        )
        self.docker_terminal_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)


    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            item = self.tree.item(selected_items[0])
            short_id = item['values'][0]  # Already short ID from tree
            container_name = item['values'][1]  # Keep name for operations
            # Display short ID in label
            self.selected_container_label.config(text=f"🆔 {short_id}")
            # Update info tab using name (Docker API needs name)
            self.display_container_info(container_name)
        else:
            self.selected_container_label.config(text="None")
            self._show_info_placeholder()

    def on_network_select(self, event):
        selected_items = self.network_tree.selection()
        if selected_items:
            item = self.network_tree.item(selected_items[0])
            network_id = item['values'][0]  # Short ID
            network_name = item['values'][1]  # Name for operations
            self.selected_container_label.config(text=f"🌐 {network_id}")
            # Update info tab using name (Docker API needs name)
            self.display_network_info(network_name)
        else:
            self.selected_container_label.config(text="None")
            self._show_info_placeholder()

    def on_image_select(self, event):
        selected = self.images_tree.selection()
        if selected:
            item = self.images_tree.item(selected[0])
            image_id = item['values'][0]  # Short ID
            # Update info tab using full image ID (stored as iid)
            self.selected_container_label.config(text=f"🖼️ {image_id}")
            # Pass the full image ID (iid) for operations
            self.display_image_info(selected[0])
        else:
            self.selected_container_label.config(text="None")
            self._show_info_placeholder()

    def on_volume_select(self, event):
        sel = self.volumes_tree.selection()
        if sel:
            item = self.volumes_tree.item(sel[0])
            volume_name = item['values'][0]
            # For volumes, show truncated name if too long (max 20 chars)
            display_name = volume_name[:20] + '...' if len(volume_name) > 20 else volume_name
            self.selected_container_label.config(text=f"💾 {display_name}")
            # Update info tab
            self.display_volume_info(volume_name)
        else:
            self.selected_container_label.config(text="None")
            self._show_info_placeholder()

    # --- Double-Click Handlers for Copying ID ---
    def on_container_double_click(self, event):
        """Copy container ID to clipboard on double-click."""
        ContainerManager.copy_container_id_to_clipboard(
            self.tree, self.clipboard_clear, self.clipboard_append, self.update, self.copy_tooltip
        )

    def on_network_double_click(self, event):
        """Copy network ID to clipboard on double-click."""
        NetworkManager.copy_network_id_to_clipboard(
            self.network_tree, self.clipboard_clear, self.clipboard_append, 
            self.update, self.copy_tooltip
        )

    def on_image_double_click(self, event):
        """Copy image ID to clipboard on double-click."""
        ImageManager.copy_image_id_to_clipboard(
            self.images_tree, self.clipboard_clear, self.clipboard_append,
            self.update, self.copy_tooltip
        )

    def on_volume_double_click(self, event):
        """Copy volume name to clipboard on double-click (volumes don't have separate IDs)."""
        VolumeManager.copy_volume_name_to_clipboard(
            self.volumes_tree, self.clipboard_clear, self.clipboard_append,
            self.update, self.copy_tooltip
        )

    # --- Info Tab Display Methods ---
    def display_container_info(self, container_name):
        """Display detailed information about a container in the Info tab."""
        ContainerManager.display_container_info(self.info_text, container_name, self.info_placeholder_label)
        self.current_info_context = {'type': 'container', 'name': container_name}

    def display_network_info(self, network_name):
        """Display detailed information about a network in the Info tab."""
        NetworkManager.display_network_info(self.info_text, network_name, self.info_placeholder_label)
        self.current_info_context = {'type': 'network', 'name': network_name}

    def display_image_info(self, image_id):
        """Display detailed information about an image in the Info tab."""
        ImageManager.display_image_info(self.info_text, image_id, self.info_placeholder_label)
        self.current_info_context = {'type': 'image', 'id': image_id}

    def display_volume_info(self, volume_name):
        """Display detailed information about a volume in the Info tab."""
        VolumeManager.display_volume_info(self.info_text, volume_name, self.info_placeholder_label)
        self.current_info_context = {'type': 'volume', 'name': volume_name}

    def _add_info_line(self, key, value):
        """Helper to add a formatted key-value line to info text."""
        InfoDisplayManager.add_info_line(self.info_text, key, value)

    def _show_info_error(self, message):
        """Display an error message in the info tab."""
        InfoDisplayManager.show_info_error(self.info_text, message)
    
    def _show_info_placeholder(self):
        """Show placeholder message in info tab when nothing is selected."""
        InfoDisplayManager.show_info_placeholder(self.info_text, self.info_placeholder_label)

    def _update_volumes_from_list(self, vol_list):
        """Update volumes tree view with volume list."""
        self.vol_tags_configured = VolumeManager.update_volumes_tree(
            self.volumes_tree, vol_list, 
            getattr(self, 'vol_tags_configured', False),
            self.BG_COLOR, self.FRAME_BG
        )

    def update_volumes_list(self):
        """Update volumes list periodically."""
        try:
            vol_list = VolumeManager.fetch_volumes()
            # Store all volumes for filtering
            self._all_volumes = vol_list
            self._update_volumes_from_list(vol_list)
            # Re-apply filter if active
            if hasattr(self, 'volumes_search_var') and self.volumes_search_var.get():
                self.filter_volumes()
        except Exception as e:
            logging.error(f"Error updating volumes list: {e}")
        finally:
            self.after(5000, self.update_volumes_list)

    def run_volume_action(self, action):
        """Execute a volume action."""
        if action == 'prune':
            VolumeManager.prune_volumes(self.refresh_all_tabs, self.status_bar)
            return
        
        VolumeManager.run_volume_action(
            self.volumes_tree, action, self.update_volumes_list, self
        )

    def _update_images_from_list(self, img_list):
        """Update images tree view with image list."""
        if not hasattr(self, 'images_tags_configured'):
            self.images_tags_configured = False
        
        self.images_tags_configured = ImageManager.update_images_tree(
            self.images_tree, img_list, self.images_tags_configured,
            self.BG_COLOR, self.FRAME_BG
        )

    def update_images_list(self):
        """Update images list periodically."""
        try:
            img_list = ImageManager.fetch_images()
            # Store all images for filtering
            self._all_images = img_list
            self._update_images_from_list(img_list)
            # Re-apply filter if active
            if hasattr(self, 'images_search_var') and self.images_search_var.get():
                self.filter_images()
        except Exception as e:
            logging.error(f"Error updating images list: {e}")
        finally:
            self.after(5000, self.update_images_list)

    def run_image_action(self, action):
        """Handle image actions."""
        sel = self.images_tree.selection()
        if action == 'pull':
            repo = simpledialog.askstring('Pull Image', 'Enter repository:tag')
            if repo:
                threading.Thread(
                    target=ImageManager.pull_image, 
                    args=(repo, self.update_images_list), 
                    daemon=True
                ).start()
            return
        
        if not sel:
            logging.warning('No image selected for action.')
            return
        
        iid = self.images_tree.item(sel[0])['values'][0]
        
        if action == 'remove':
            confirm_callback = lambda msg: messagebox.askyesno('Confirm Remove', msg)
            if ImageManager.remove_image(iid, confirm_callback):
                self.update_images_list()
        elif action == 'inspect':
            ImageManager.show_image_inspect_modal(self, iid)

    def pull_image(self, repo):
        """Wrapper for backward compatibility."""
        ImageManager.pull_image(repo, self.update_images_list)

    def run_dashboard_action(self, action):
        """Handle dashboard tab actions."""
        if action == 'refresh':
            self.refresh_dashboard()
            logging.info('Dashboard refreshed')
        elif action == 'prune':
            self.prune_system()

    def run_compose_action(self, action):
        """Handle compose tab actions."""
        if action == 'up':
            self.compose_up()
        elif action == 'down':
            self.compose_down()
        elif action == 'restart':
            self.compose_restart()
        elif action == 'logs':
            self.compose_logs()

    def run_info_action(self, action):
        """Handle info tab actions."""
        if action == 'refresh':
            # Refresh the current info display
            if self.current_info_context.get('type') == 'container':
                name = self.current_info_context.get('name')
                if name:
                    self.display_container_info(name)
                    logging.info(f'Info refreshed for container: {name}')
            elif self.current_info_context.get('type') == 'network':
                name = self.current_info_context.get('name')
                if name:
                    self.display_network_info(name)
                    logging.info(f'Info refreshed for network: {name}')
            elif self.current_info_context.get('type') == 'image':
                iid = self.current_info_context.get('id')
                if iid:
                    self.display_image_info(iid)
                    logging.info(f'Info refreshed for image: {iid}')
            elif self.current_info_context.get('type') == 'volume':
                name = self.current_info_context.get('name')
                if name:
                    self.display_volume_info(name)
                    logging.info(f'Info refreshed for volume: {name}')
        elif action == 'copy':
            # Copy info text to clipboard
            try:
                text = self.info_text.get('1.0', tk.END)
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update()
                logging.info('Info copied to clipboard')
                messagebox.showinfo('Success', 'Information copied to clipboard!')
            except Exception as e:
                logging.error(f'Failed to copy info: {e}')

    def run_help_action(self, action):
        """Handle help tab actions."""
        # Switch to help tab
        try:
            self.notebook.select(7)  # Help tab index
            
            # Scroll to specific section
            if action in self.help_sections:
                widget = self.help_sections[action]
                
                # Schedule scroll after tab is fully rendered
                def scroll_to_section():
                    try:
                        # Update canvas to ensure everything is rendered
                        self.help_canvas.update_idletasks()
                        
                        # Get the canvas window
                        canvas_window = self.help_canvas.find_withtag("all")[0]
                        
                        # Get widget's position relative to its parent
                        widget_y = widget.winfo_y()
                        
                        # Get scroll region
                        scrollregion = self.help_canvas.cget("scrollregion")
                        if scrollregion:
                            # Parse scrollregion: "x1 y1 x2 y2"
                            parts = scrollregion.split()
                            total_height = float(parts[3]) - float(parts[1])
                            
                            if total_height > 0:
                                # Calculate fraction to scroll (put section at top with small padding)
                                fraction = max(0, (widget_y - 20) / total_height)
                                self.help_canvas.yview_moveto(fraction)
                                logging.info(f'Scrolled to {action} section in Help')
                    except Exception as e:
                        logging.error(f'Error scrolling to section: {e}')
                
                # Delay scroll to ensure tab is fully rendered
                self.after(50, scroll_to_section)
            else:
                # Just go to top if section not found
                self.help_canvas.yview_moveto(0.0)
                logging.info(f'Navigated to Help tab')
                
        except Exception as e:
            logging.error(f'Error navigating to help section: {e}')

    def _on_tab_changed(self, event):
        # Show appropriate action panel in controls depending on active tab
        try:
            tab_text = event.widget.tab(event.widget.select(), 'text')
        except Exception:
            return

        # default: hide all action panels
        try:
            self.container_actions_panel.pack_forget()
            self.network_actions_panel.pack_forget()
            self.images_actions_panel.pack_forget()
            self.volumes_actions_panel.pack_forget()
            self.dashboard_actions_panel.pack_forget()
            self.compose_actions_panel.pack_forget()
            self.info_actions_panel.pack_forget()
            self.help_actions_panel.pack_forget()
            self.settings_actions_panel.pack_forget()
        except Exception:
            pass

        # Determine if we should show the "Selected Item" section
        # Only show for tabs that have selectable items (Containers, Network, Images, Volumes)
        show_selected = any(x in tab_text for x in ['📦 Containers', '🌐 Network', '🖼️ Images', '💾 Volumes'])
        
        try:
            if show_selected:
                self.selected_section_frame.pack(pady=(10, 5), padx=10, fill=tk.X)
            else:
                self.selected_section_frame.pack_forget()
        except Exception:
            pass

        # Match tab names with emojis
        if '📦 Containers' in tab_text:
            self.container_actions_panel.pack(fill=tk.BOTH, expand=True)
            # show container footer (global actions + config)
            try:
                self.container_footer_panel.pack(pady=0, padx=0, fill=tk.X)
            except Exception:
                pass
        elif '🌐 Network' in tab_text:
            self.network_actions_panel.pack(fill=tk.BOTH, expand=True)
            # hide container footer when viewing networks
            try:
                self.container_footer_panel.pack_forget()
            except Exception:
                pass
        elif '🖼️ Images' in tab_text:
            self.images_actions_panel.pack(fill=tk.BOTH, expand=True)
            try:
                self.container_footer_panel.pack_forget()
            except Exception:
                pass
        elif '💾 Volumes' in tab_text:
            self.volumes_actions_panel.pack(fill=tk.BOTH, expand=True)
            try:
                self.container_footer_panel.pack_forget()
            except Exception:
                pass
        elif '📊 Dashboard' in tab_text:
            self.dashboard_actions_panel.pack(fill=tk.BOTH, expand=True)
            try:
                self.container_footer_panel.pack_forget()
            except Exception:
                pass
        elif '🐳 Compose' in tab_text:
            self.compose_actions_panel.pack(fill=tk.BOTH, expand=True)
            try:
                self.container_footer_panel.pack_forget()
            except Exception:
                pass
        elif '💡 Info' in tab_text:
            self.info_actions_panel.pack(fill=tk.BOTH, expand=True)
            try:
                self.container_footer_panel.pack_forget()
            except Exception:
                pass
        elif '📚 Help' in tab_text:
            self.help_actions_panel.pack(fill=tk.BOTH, expand=True)
            try:
                self.container_footer_panel.pack_forget()
            except Exception:
                pass
        elif '⚙️ Settings' in tab_text:
            self.settings_actions_panel.pack(fill=tk.BOTH, expand=True)
            try:
                self.container_footer_panel.pack_forget()
            except Exception:
                pass

    def _update_network_from_list(self, net_list):
        """Update network tree view with network list."""
        if not hasattr(self, 'network_tree_tags_configured'):
            self.network_tree_tags_configured = False
        
        self.network_tree_tags_configured = NetworkManager.update_network_tree(
            self.network_tree, net_list, self.network_tree_tags_configured, 
            self.BG_COLOR, self.FRAME_BG
        )

    def update_network_list(self):
        """Update network list periodically."""
        try:
            net_list = NetworkManager.fetch_networks()
            # Store all networks for filtering
            self._all_networks = net_list
            self._update_network_from_list(net_list)
            # Re-apply filter if active
            if hasattr(self, 'network_search_var') and self.network_search_var.get():
                self.filter_networks()
        except Exception as e:
            logging.error(f"Error updating network list: {e}")
        finally:
            self.after(5000, self.update_network_list)

    def _fetch_networks_for_refresh(self):
        """Fetch networks for manual refresh."""
        NetworkManager.fetch_networks_for_refresh()

    def force_refresh_active_tab(self):
        if not hasattr(self, 'notebook'):
            return
        tab = self.notebook.tab(self.notebook.select(), 'text')
        if tab == 'Containers':
            self.force_refresh_containers()
        elif tab == 'Network':
            threading.Thread(target=self._fetch_networks_for_refresh, daemon=True).start()

    def run_network_action(self, action):
        selected_items = self.network_tree.selection()
        # Some actions (create/prune) do not need a selected network
        if action == 'create':
            self.create_network()
            return
        if action == 'prune':
            self.prune_networks()
            return

        if not selected_items:
            logging.warning("No network selected for action.")
            return

        item = self.network_tree.item(selected_items[0])
        network_name = item['values'][1]
        logging.info(f"User requested '{action}' on network '{network_name}'.")
        with docker_lock:
            try:
                net = client.networks.get(network_name)
                if action == 'remove':
                    confirm = messagebox.askyesno("Confirm Remove", f"Remove network '{network_name}'? This may disconnect containers.")
                    if confirm:
                        net.remove()
                        logging.info(f"Removed network {network_name}.")
                        # refresh network list immediately
                        self.update_network_list()
                elif action == 'inspect':
                    self._show_network_inspect_modal(net)
                elif action == 'connect':
                    self.connect_container_to_network(net)
                elif action == 'disconnect':
                    self.disconnect_container_from_network(net)
            except Exception as e:
                logging.error(f"Error during '{action}' on network '{network_name}': {e}")

    def _show_network_inspect_modal(self, net):
        try:
            data = net.attrs
        except Exception:
            data = {}

        win = tk.Toplevel(self)
        win.title(f"Inspect: {net.name}")
        win.transient(self)
        win.grab_set()

        frame = ttk.Frame(win, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        # Show connected containers summary if available
        containers = data.get('Containers') if isinstance(data, dict) else None
        if containers:
            info = "Connected Containers:\n"
            for cname, cinfo in containers.items():
                info += f"- {cname}: {cinfo.get('Name', '')}\n"
            lbl = tk.Label(frame, text=info, justify='left')
            lbl.pack(fill=tk.X, pady=(0,8))

        txt = scrolledtext.ScrolledText(frame, height=20, wrap=tk.NONE, bg='#ffffff', fg='#000000')
        txt.pack(fill=tk.BOTH, expand=True)
        try:
            txt.insert(tk.END, json.dumps(data, indent=2))
        except Exception:
            txt.insert(tk.END, str(data))
        txt.config(state='disabled')

        btn = ttk.Button(frame, text='Close', command=win.destroy)
        btn.pack(pady=8)

    def create_network(self):
        """Create a new Docker network."""
        name_callback = lambda: simpledialog.askstring("Create Network", "Enter network name:")
        driver_callback = lambda: simpledialog.askstring("Create Network", "Driver (bridge/overlay/etc):", initialvalue='bridge')
        success_callback = lambda: self.update_network_list()
        
        NetworkManager.create_network(name_callback, driver_callback, success_callback)

    def connect_container_to_network(self, net):
        """Show a dialog with list of all containers to connect to the network."""
        # Run container fetching in a separate thread to avoid UI hang
        def fetch_and_show():
            try:
                # Get all containers in background thread
                with docker_lock:
                    all_containers = client.containers.list(all=True)
                
                # Schedule UI update in main thread
                self.after(0, lambda: self._show_connect_dialog(net, all_containers))
            
            except Exception as e:
                logging.error(f"Error fetching containers: {e}")
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to load containers: {str(e)}"))
                self.after(0, lambda: self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager"))
        
        # Show loading message
        self.status_bar.config(text="🔄 Loading containers...")
        self.update_idletasks()
        
        # Start background thread
        threading.Thread(target=fetch_and_show, daemon=True).start()
    
    def _show_connect_dialog(self, net, all_containers):
        """Show the container selection dialog (runs in main thread)."""
        try:
            self.status_bar.config(text=f"Ready | Found {len(all_containers)} containers")
            
            if not all_containers:
                messagebox.showinfo("No Containers", "No containers available to connect.")
                self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager")
                return
            
            # Create selection dialog
            dialog = tk.Toplevel(self)
            dialog.title(f"Connect Container to Network: {net.name}")
            dialog.geometry("500x400")
            dialog.configure(bg='#1e2a35')
            dialog.transient(self)
            dialog.grab_set()
            
            # Center the dialog
            dialog.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
            y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")
            
            # Title label
            title_label = tk.Label(
                dialog,
                text=f"🔗 Select Container to Connect to '{net.name}'",
                font=('Segoe UI', 12, 'bold'),
                bg='#1e2a35',
                fg='#00d4ff',
                pady=10
            )
            title_label.pack(fill=tk.X)
            
            # Info label
            info_label = tk.Label(
                dialog,
                text="Select a container from the list below:",
                font=('Segoe UI', 9),
                bg='#1e2a35',
                fg='#aaaaaa',
                pady=5
            )
            info_label.pack()
            
            # Frame for listbox and scrollbar
            list_frame = tk.Frame(dialog, bg='#1e2a35')
            list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            # Scrollbar
            scrollbar = tk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Listbox with container names
            container_listbox = tk.Listbox(
                list_frame,
                yscrollcommand=scrollbar.set,
                font=('Consolas', 10),
                bg='#2a3a4a',
                fg='#ffffff',
                selectmode=tk.SINGLE,
                selectbackground='#00ADB5',
                selectforeground='#ffffff',
                relief='flat',
                borderwidth=2,
                highlightthickness=0
            )
            container_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=container_listbox.yview)
            
            # Populate listbox with container info
            container_map = {}
            for container in all_containers:
                status_icon = "🟢" if container.status == "running" else "🔴" if container.status == "exited" else "🟡"
                display_text = f"{status_icon} {container.name} ({container.status})"
                container_listbox.insert(tk.END, display_text)
                container_map[display_text] = container
            
            # Selected container variable
            selected_container = [None]
            
            def on_select():
                selection = container_listbox.curselection()
                if selection:
                    selected_text = container_listbox.get(selection[0])
                    selected_container[0] = container_map[selected_text]
                    dialog.destroy()
            
            def on_cancel():
                dialog.destroy()
            
            # Double-click to select
            container_listbox.bind('<Double-Button-1>', lambda e: on_select())
            
            # Buttons frame
            button_frame = tk.Frame(dialog, bg='#1e2a35')
            button_frame.pack(fill=tk.X, padx=20, pady=10)
            
            connect_btn = tk.Button(
                button_frame,
                text="✓ Connect",
                command=on_select,
                bg='#28a745',
                fg='white',
                font=('Segoe UI', 10, 'bold'),
                relief='flat',
                cursor='hand2',
                padx=20,
                pady=8
            )
            connect_btn.pack(side=tk.LEFT, padx=5)
            
            cancel_btn = tk.Button(
                button_frame,
                text="✖ Cancel",
                command=on_cancel,
                bg='#d32f2f',
                fg='white',
                font=('Segoe UI', 10, 'bold'),
                relief='flat',
                cursor='hand2',
                padx=20,
                pady=8
            )
            cancel_btn.pack(side=tk.LEFT, padx=5)
            
            # Wait for dialog to close
            self.wait_window(dialog)
            
            # Connect the selected container
            if selected_container[0]:
                try:
                    self.status_bar.config(text=f"Connecting {selected_container[0].name} to {net.name}...")
                    self.update_idletasks()
                    
                    net.connect(selected_container[0])
                    logging.info(f"Connected container {selected_container[0].name} to network {net.name}.")
                    
                    self.status_bar.config(text=f"Ready | Container connected successfully")
                    messagebox.showinfo("Success", f"Container '{selected_container[0].name}' connected to network '{net.name}'.")
                    self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager")
                except Exception as e:
                    logging.error(f"Failed to connect container to network: {e}")
                    messagebox.showerror("Error", f"Failed to connect container: {str(e)}")
                    self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager")
            else:
                self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager")
        
        except Exception as e:
            logging.error(f"Error showing container selection dialog: {e}")
            messagebox.showerror("Error", f"Failed to show dialog: {str(e)}")
            self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager")

    def disconnect_container_from_network(self, net):
        """Show a dialog with list of connected containers to disconnect from the network."""
        # Run fetching in a separate thread to avoid UI hang
        def fetch_and_show():
            try:
                # Get network details in background thread
                with docker_lock:
                    net.reload()
                    connected_containers = net.attrs.get('Containers', {})
                
                # Schedule UI update in main thread
                self.after(0, lambda: self._show_disconnect_dialog(net, connected_containers))
            
            except Exception as e:
                logging.error(f"Error fetching connected containers: {e}")
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to load connected containers: {str(e)}"))
                self.after(0, lambda: self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager"))
        
        # Show loading message
        self.status_bar.config(text="🔄 Loading connected containers...")
        self.update_idletasks()
        
        # Start background thread
        threading.Thread(target=fetch_and_show, daemon=True).start()
    
    def _show_disconnect_dialog(self, net, connected_containers):
        """Show the disconnect dialog (runs in main thread)."""
        try:
            self.status_bar.config(text=f"Ready | Found {len(connected_containers)} connected containers")
            
            if not connected_containers:
                messagebox.showinfo("No Containers", f"No containers are connected to network '{net.name}'.")
                self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager")
                return
            
            # Create selection dialog
            dialog = tk.Toplevel(self)
            dialog.title(f"Disconnect Container from Network: {net.name}")
            dialog.geometry("500x400")
            dialog.configure(bg='#1e2a35')
            dialog.transient(self)
            dialog.grab_set()
            
            # Center the dialog
            dialog.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
            y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")
            
            # Title label
            title_label = tk.Label(
                dialog,
                text=f"❌ Select Container to Disconnect from '{net.name}'",
                font=('Segoe UI', 12, 'bold'),
                bg='#1e2a35',
                fg='#ff6b6b',
                pady=10
            )
            title_label.pack(fill=tk.X)
            
            # Info label
            info_label = tk.Label(
                dialog,
                text="Select a connected container from the list below:",
                font=('Segoe UI', 9),
                bg='#1e2a35',
                fg='#aaaaaa',
                pady=5
            )
            info_label.pack()
            
            # Frame for listbox and scrollbar
            list_frame = tk.Frame(dialog, bg='#1e2a35')
            list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            # Scrollbar
            scrollbar = tk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Listbox with connected container names
            container_listbox = tk.Listbox(
                list_frame,
                yscrollcommand=scrollbar.set,
                font=('Consolas', 10),
                bg='#2a3a4a',
                fg='#ffffff',
                selectmode=tk.SINGLE,
                selectbackground='#00ADB5',
                selectforeground='#ffffff',
                relief='flat',
                borderwidth=2,
                highlightthickness=0
            )
            container_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=container_listbox.yview)
            
            # Populate listbox with connected containers
            container_id_map = {}
            for container_id, container_info in connected_containers.items():
                container_name = container_info.get('Name', 'Unknown')
                ip_address = container_info.get('IPv4Address', 'No IP').split('/')[0]
                display_text = f"🔗 {container_name} ({ip_address})"
                container_listbox.insert(tk.END, display_text)
                container_id_map[display_text] = container_name
            
            # Selected container variable
            selected_container_name = [None]
            
            def on_select():
                selection = container_listbox.curselection()
                if selection:
                    selected_text = container_listbox.get(selection[0])
                    selected_container_name[0] = container_id_map[selected_text]
                    dialog.destroy()
            
            def on_cancel():
                dialog.destroy()
            
            # Double-click to select
            container_listbox.bind('<Double-Button-1>', lambda e: on_select())
            
            # Buttons frame
            button_frame = tk.Frame(dialog, bg='#1e2a35')
            button_frame.pack(fill=tk.X, padx=20, pady=10)
            
            disconnect_btn = tk.Button(
                button_frame,
                text="✓ Disconnect",
                command=on_select,
                bg='#dc3545',
                fg='white',
                font=('Segoe UI', 10, 'bold'),
                relief='flat',
                cursor='hand2',
                padx=20,
                pady=8
            )
            disconnect_btn.pack(side=tk.LEFT, padx=5)
            
            cancel_btn = tk.Button(
                button_frame,
                text="✖ Cancel",
                command=on_cancel,
                bg='#6c757d',
                fg='white',
                font=('Segoe UI', 10, 'bold'),
                relief='flat',
                cursor='hand2',
                padx=20,
                pady=8
            )
            cancel_btn.pack(side=tk.LEFT, padx=5)
            
            # Wait for dialog to close
            self.wait_window(dialog)
            
            # Disconnect the selected container
            if selected_container_name[0]:
                try:
                    self.status_bar.config(text=f"Disconnecting {selected_container_name[0]} from {net.name}...")
                    self.update_idletasks()
                    
                    container = client.containers.get(selected_container_name[0])
                    net.disconnect(container)
                    logging.info(f"Disconnected container {selected_container_name[0]} from network {net.name}.")
                    
                    self.status_bar.config(text=f"Ready | Container disconnected successfully")
                    messagebox.showinfo("Success", f"Container '{selected_container_name[0]}' disconnected from network '{net.name}'.")
                    self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager")
                except Exception as e:
                    logging.error(f"Failed to disconnect container from network: {e}")
                    messagebox.showerror("Error", f"Failed to disconnect container: {str(e)}")
                    self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager")
            else:
                self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager")
        
        except Exception as e:
            logging.error(f"Error showing connected containers dialog: {e}")
            messagebox.showerror("Error", f"Failed to show dialog: {str(e)}")
            self.status_bar.config(text="Ready | 🐳 Docker Monitor Manager")

    def run_container_action(self, action):
        """Wrapper for ContainerManager.run_container_action."""
        ContainerManager.run_container_action(self.tree, action)

    def run_global_action(self, action):
        """Wrapper for ContainerManager.run_global_action."""
        ContainerManager.run_global_action(action)

    def force_refresh_containers(self):
        """Immediately fetches all container stats and updates the GUI tree."""
        logging.info("User requested manual container list refresh.")
        # Run the blocking Docker API calls in a separate thread
        threading.Thread(target=self._fetch_all_stats_for_refresh, daemon=True).start()

    def _fetch_all_stats_for_refresh(self):
        """Worker function for the manual refresh thread."""
        stats_list = ContainerManager.fetch_all_stats()
        if stats_list:
            manual_refresh_queue.put(stats_list)

    def open_config_window(self):
        """Opens a Toplevel window to configure monitoring settings."""
        config_window = tk.Toplevel(self)
        config_window.title("Configuration")
        config_window.configure(bg=self.BG_COLOR)
        config_window.transient(self)  # Keep it on top of the main window
        config_window.grab_set()       # Modal behavior

        # Center the window
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_w = self.winfo_width()
        main_h = self.winfo_height()
        win_w = 300
        win_h = 250
        pos_x = main_x + (main_w // 2) - (win_w // 2)
        pos_y = main_y + (main_h // 2) - (win_h // 2)
        config_window.geometry(f'{win_w}x{win_h}+{pos_x}+{pos_y}')

        frame = tk.Frame(config_window, bg=self.BG_COLOR, padx=10, pady=10)
        frame.pack(expand=True, fill=tk.BOTH)

        # --- Labels and Entries ---
        ttk.Label(frame, text="CPU Limit (%)").grid(row=0, column=0, sticky="w", pady=5)
        cpu_var = tk.StringVar(value=str(CPU_LIMIT))
        cpu_entry = tk.Entry(frame, textvariable=cpu_var, fg="black")
        cpu_entry.grid(row=0, column=1, sticky="ew")

        ttk.Label(frame, text="RAM Limit (%)").grid(row=1, column=0, sticky="w", pady=5)
        ram_var = tk.StringVar(value=str(RAM_LIMIT))
        ram_entry = tk.Entry(frame, textvariable=ram_var, fg="black")
        ram_entry.grid(row=1, column=1, sticky="ew")

        ttk.Label(frame, text="Max Clones").grid(row=2, column=0, sticky="w", pady=5)
        clone_var = tk.StringVar(value=str(CLONE_NUM))
        clone_entry = tk.Entry(frame, textvariable=clone_var, fg="black")
        clone_entry.grid(row=2, column=1, sticky="ew")

        ttk.Label(frame, text="Check Interval (s)").grid(row=3, column=0, sticky="w", pady=5)
        sleep_var = tk.StringVar(value=str(SLEEP_TIME))
        sleep_entry = tk.Entry(frame, textvariable=sleep_var, fg="black")
        sleep_entry.grid(row=3, column=1, sticky="ew")

        frame.columnconfigure(1, weight=1)

        def save_config():
            global CPU_LIMIT, RAM_LIMIT, CLONE_NUM, SLEEP_TIME
            try:
                new_cpu = float(cpu_var.get())
                new_ram = float(ram_var.get())
                new_clones = int(clone_var.get())
                new_sleep = int(sleep_var.get())

                CPU_LIMIT = new_cpu
                RAM_LIMIT = new_ram
                CLONE_NUM = new_clones
                SLEEP_TIME = new_sleep

                logging.info(f"Configuration updated: CPU={new_cpu}%, RAM={new_ram}%, Clones={new_clones}, Interval={new_sleep}s")
                config_window.destroy()
            except ValueError:
                logging.error("Invalid configuration value. Please enter valid numbers.")
                # Optionally show an error message in the dialog

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        ttk.Button(button_frame, text="Save", command=save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=config_window.destroy).pack(side=tk.LEFT, padx=5)

    def _update_tree_from_stats(self, stats_list):
        """Helper function to update the Treeview from a list of stats."""
        # Store all containers data for filtering
        self._all_containers = stats_list
        
        # Apply filter if search is active
        if hasattr(self, 'container_search_var') and self.container_search_var.get():
            self.filter_containers()
            return
            
        # Update tree with all containers
        self._apply_containers_to_tree(stats_list)
    
    def _apply_containers_to_tree(self, stats_list):
        """Apply container list to tree view."""
        self.tree_tags_configured = ContainerManager.apply_containers_to_tree(
            self.tree, stats_list, self.tree_tags_configured, self.BG_COLOR, self.FRAME_BG
        )
    
    def filter_containers(self):
        """Filter containers based on search query."""
        if not hasattr(self, '_all_containers'):
            return
            
        search_text = self.container_search_var.get()
        filtered = ContainerManager.filter_containers(self._all_containers, search_text)
        self._apply_containers_to_tree(filtered)

    def filter_networks(self):
        """Filter networks based on search query."""
        if not hasattr(self, '_all_networks'):
            return
            
        search_text = self.network_search_var.get()
        filtered = NetworkManager.filter_networks(self._all_networks, search_text)
        self._update_network_from_list(filtered)

    def filter_images(self):
        """Filter images based on search query."""
        if not hasattr(self, '_all_images'):
            return
            
        search_text = self.images_search_var.get()
        filtered = ImageManager.filter_images(self._all_images, search_text)
        self._update_images_from_list(filtered)

    def filter_volumes(self):
        """Filter volumes based on search query."""
        if not hasattr(self, '_all_volumes'):
            return
        
        VolumeManager.filter_volumes(
            self.volumes_tree, self._all_volumes, 
            self.volumes_search_var, self.BG_COLOR, self.FRAME_BG
        )

    def update_container_list(self):
        """Checks the queue for new stats and updates the Treeview."""
        try:
            # First, check for manual refresh data, which has priority
            while not manual_refresh_queue.empty():
                stats_list = manual_refresh_queue.get_nowait()
                self._update_tree_from_stats(stats_list)
                # Clear the regular queue to avoid showing stale data right after a refresh
                while not stats_queue.empty():
                    stats_queue.get_nowait()

            while not stats_queue.empty():
                stats_list = stats_queue.get_nowait()

                # Use the helper to update the tree from the queued stats
                self._update_tree_from_stats(stats_list)

        except queue.Empty:
            pass
        finally:
            # Schedule the next check
            self.after(1000, self.update_container_list)

    def _reapply_row_tags(self):
        """Wrapper for ContainerManager.reapply_row_tags."""
        ContainerManager.reapply_row_tags(self.tree)

    def update_logs(self):
        """Periodically checks the log buffer and appends new entries."""
        if len(log_buffer) > self.log_update_idx:
            self.log_text.config(state='normal')
            for i in range(self.log_update_idx, len(log_buffer)):
                self.log_text.insert(tk.END, log_buffer[i] + '\n')
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
            self.log_update_idx = len(log_buffer)
        
        self.after(1000, self.update_logs)
    
    def update_status_bar(self):
        """Update status bar with system information."""
        try:
            with docker_lock:
                containers = client.containers.list(all=True)
                running = sum(1 for c in containers if c.status == 'running')
                total = len(containers)
                images = len(client.images.list())
                volumes = len(client.volumes.list())
                networks = len(client.networks.list())
                
            status_text = f"Ready | 🐳 Docker: {running}/{total} containers running | 🖼️ {images} images | 💾 {volumes} volumes | 🌐 {networks} networks"
            self.status_bar.config(text=status_text)
        except Exception as e:
            self.status_bar.config(text=f"Error: {str(e)}")
        finally:
            self.after(5000, self.update_status_bar)
    
    def set_status(self, message, duration=3000):
        """Set temporary status message."""
        self.status_bar.config(text=message, fg='#00ff88')
        self.after(duration, self.update_status_bar)


def main():
    """Main entry point for the Docker-Monitor-Manager application."""
    import platform
    
    # Check if desktop entry is installed (Linux only)
    if platform.system() == "Linux":
        desktop_file = Path.home() / ".local/share/applications/docker-monitor-manager.desktop"
        if not desktop_file.exists():
            print("\n" + "="*60)
            print("⚠️  Desktop entry not installed!")
            print("="*60)
            print("To add Docker Monitor Manager to your application menu,")
            print("please run:")
            print("")
            print("    dmm-setup")
            print("")
            print("Or manually run:")
            print("    python3 setup_tools/post_install.py")
            print("="*60 + "\n")
    
    # Start the background monitoring thread
    monitor = threading.Thread(target=monitor_thread, daemon=True)
    monitor.start()
    
    # Start the Docker events listener thread for real-time updates
    events_listener = threading.Thread(target=docker_events_listener, daemon=True)
    events_listener.start()

    # Start the Tkinter GUI
    app = DockerMonitorApp()
    app.mainloop()


if __name__ == "__main__":
    main()