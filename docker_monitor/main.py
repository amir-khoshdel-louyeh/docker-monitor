import docker
import time
import logging
from collections import deque
import queue
import threading
import subprocess
import argparse
import tkinter as tk # Keep this for the main app
from tkinter import ttk, scrolledtext

log_buffer = deque(maxlen=1000)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class BufferHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        log_buffer.append(log_entry)

buffer_handler = BufferHandler()
buffer_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logging.getLogger().addHandler(buffer_handler)


# --- Configuration ---
CPU_LIMIT = 50.0  # %
RAM_LIMIT = 5.0   # %
CLONE_NUM = 2     # Max clones per container
SLEEP_TIME = 4    # Polling interval in seconds


# --- Docker Client and Logic (adapted from app.py) ---
try:
    client = docker.from_env()
    client.ping()
    logging.info("Docker client connected successfully!")
except Exception as e:
    logging.error(f"Docker client failed to connect: {e}")
    exit(1)

stats_queue = queue.Queue()
manual_refresh_queue = queue.Queue() # A dedicated queue for manual refresh results
docker_lock = threading.Lock() # A lock to prevent race conditions on Docker operations



def calculate_cpu_percent(stats):
    try:
        cpu_current = stats['cpu_stats']['cpu_usage']['total_usage']
        cpu_prev = stats['precpu_stats']['cpu_usage']['total_usage']
       
        system_current = stats['cpu_stats']['system_cpu_usage']
        system_prev = stats['precpu_stats']['system_cpu_usage']

        cpu_delta = cpu_current - cpu_prev
        system_delta = system_current - system_prev

        num_cpus = stats['cpu_stats'].get('online_cpus', 1)
        
        if system_delta > 0 and cpu_delta > 0:
            CPU_percent = (cpu_delta / system_delta) * num_cpus * 100.0
        else:
            CPU_percent = 0.0

        return CPU_percent
    except (KeyError, TypeError):
        pass
    return 0.0

def calculate_ram_percent(stats):
    try:
        mem_usage = stats['memory_stats'].get('usage', 0)
        mem_limit = stats['memory_stats'].get('limit', 1)
        return (mem_usage / mem_limit) * 100.0
    except (KeyError, TypeError):
        pass
    return 0.0

def get_container_stats(container):
    try:
        stats = container.stats(stream=False)

        cpu = calculate_cpu_percent(stats)
        ram = calculate_ram_percent(stats)
        return {
            'id': container.short_id,
            'name': container.name,
            'status': container.status,
            'cpu': f"{cpu:.2f}",
            'ram': f"{ram:.2f}"
        }
    except Exception:
        return {'id': container.short_id, 'name': container.name, 'status': 'error', 'cpu': '0.00', 'ram': '0.00'}

def delete_clones(container, all_containers):
    base_name = container.name.split("_clone")[0]
    existing_clones = [c for c in all_containers if c.name.startswith(base_name + "_clone")]
    for clone in existing_clones:
        try:
            clone.stop()
            clone.remove()
            logging.info(f"Deleted clone container {clone.name}.")
        except Exception as e:
            logging.error(f"Failed to delete clone container {clone.name}: {e}")


# --- Docker Cleanup Function ---
def docker_cleanup():
    #logging.info("Starting Docker cleanup...")
    try:
        # Use the Docker SDK for a cleaner and more robust implementation
        client.images.prune(filters={'dangling': True})  # Prune dangling images created by .commit()
        #logging.info("Pruned dangling images.")
        client.volumes.prune()
        #logging.info("Pruned unused volumes. Docker cleanup finished.")
    except Exception as e:
        logging.error(f"An error occurred during Docker cleanup: {e}")

# --- داخل scale_container اضافه کن ---
def scale_container(container, all_containers):
    container_name = container.name
    existing_clones = [c for c in all_containers if c.name.startswith(container_name + "_clone")]

    if len(existing_clones) >= CLONE_NUM:
        logging.info(f"Max clones reached for '{container_name}'. Pausing original and deleting clones.")
        try:
            container.pause()
            logging.info(f"Paused original container '{container_name}'.")
        except Exception as e:
            logging.error(f"Failed to pause original container '{container_name}': {e}")
        delete_clones(container, all_containers)
        # Run cleanup in a separate thread to avoid blocking
        threading.Thread(target=docker_cleanup, daemon=True).start()
        return

    clone_name = f"{container_name}_clone{len(existing_clones) + 1}"
    try:
        temp_image = container.commit()
        client.containers.run(image=temp_image.id, name=clone_name, detach=True)
        logging.info(f"Successfully created clone container '{clone_name}'.")
    except Exception as e:
        logging.error(f"Error creating clone container '{clone_name}': {e}")
    
    # Run cleanup in a separate thread to avoid blocking
    threading.Thread(target=docker_cleanup, daemon=True).start()



def monitor_thread():
    global SLEEP_TIME

    while True:
        with docker_lock:
            try:

                all_containers = client.containers.list(all=True)
                stats_list = []
                for container in all_containers:
                    stats = get_container_stats(container)
                    stats_list.append(stats)

                    # --- Auto-scaling logic ---
                    # Only consider 'running' containers for scaling to avoid race conditions with paused ones.
                    if container.status == 'running':
                        cpu_float = float(stats['cpu'])
                        ram_float = float(stats['ram'])

                        if (cpu_float > CPU_LIMIT or ram_float > RAM_LIMIT) and "_clone" not in container.name:
                            logging.info(f"Container {container.name} overloaded (CPU: {cpu_float:.2f}%, RAM: {ram_float:.2f}%). Scaling...")
                            scale_container(container, all_containers)
                            
                # Put the entire list into the queue for the GUI to process
                stats_queue.put(stats_list)

            except Exception as e:
                logging.error(f"Error in monitor loop: {e}")
        
        time.sleep(SLEEP_TIME)


# --- Docker Terminal Widget (merged from docker_terminal.py) ---
class DockerTerminal(tk.Frame):
    # A sentinel object to signal when to add a new prompt
    _PROMPT_SENTINEL = object()
    _POLL_INTERVAL_MS = 100

    def __init__(self, master, **kwargs):
        super().__init__(master)

        # The internal Text widget receives styling arguments from the parent
        self.terminal_output = tk.Text(self, **kwargs)
        self.terminal_output.pack(expand=True, fill=tk.BOTH)

        # --- Event Bindings ---
        self.terminal_output.bind("<Return>", self.run_terminal_command)
        self.terminal_output.bind("<Key>", self.handle_key_press)
        self.terminal_output.bind("<Up>", self.handle_history)
        self.terminal_output.bind("<Down>", self.handle_history)

        # --- State Management ---
        self.command_history = []
        self.history_index = 0
        self.output_queue = queue.Queue()
        self.is_polling = False

        # Configure error tag for security messages
        self.terminal_output.tag_config('error_tag', foreground='#e74c3c')

        # Add the initial prompt
        self.add_new_prompt()

    def add_new_prompt(self):
        """Adds a new input prompt to the terminal."""
        # Ensure there's a newline before the prompt, unless it's the very first line
        current_content = self.terminal_output.get("1.0", tk.END)
        if current_content.strip() and not current_content.endswith('\n'):
            self.terminal_output.insert(tk.END, "\n")

        self.terminal_output.insert(tk.END, "$ ")
        self.terminal_output.mark_set("input_start", "end-2c") # Mark start of user input
        self.terminal_output.see(tk.END)

    def handle_key_press(self, event):
        """Prevents deletion of the prompt or text before it."""
        if self.terminal_output.index(tk.INSERT) < self.terminal_output.index("input_start"):
            # If a printable character is typed, move the cursor to the end.
            # Otherwise (e.g., Backspace, Delete), block the action.
            if event.char and event.char.isprintable():
                self.terminal_output.mark_set(tk.INSERT, tk.END)
            else:
                return "break"

    def handle_history(self, event):
        """Manages command history navigation with arrow keys."""
        if not self.command_history:
            return "break"

        if event.keysym == "Up":
            self.history_index = max(0, self.history_index - 1)
        elif event.keysym == "Down":
            self.history_index = min(len(self.command_history), self.history_index + 1)

        # Clear current input
        self.terminal_output.delete("input_start", tk.END)

        # Show history item or blank if at the end
        if self.history_index < len(self.command_history):
            self.terminal_output.insert(tk.END, self.command_history[self.history_index])

        return "break"

    def run_terminal_command(self, event):
        command_str = self.terminal_output.get("input_start", tk.END).strip()

        # Move to a new line and disable editing of the just-entered command
        self.terminal_output.insert(tk.END, "\n")
        self.terminal_output.mark_unset("input_start")

        if not command_str:
            self.add_new_prompt()
            return "break"

        # Add to history and reset index
        if command_str not in self.command_history:
            self.command_history.append(command_str)
        self.history_index = len(self.command_history)

        # Handle 'clear' command locally in the GUI
        if command_str.lower() == "clear":
            self.terminal_output.delete("1.0", tk.END)
            self.add_new_prompt()
            return "break"

        
        # Security: Only allow 'docker' commands
        command_parts = command_str.split()
        if not command_parts or command_parts[0] != "docker":
            msg = "Security Error: Only 'docker' commands are allowed.\n"
            logging.warning(msg.strip())
            self.terminal_output.insert(tk.END, msg, 'error_tag')
            self.add_new_prompt()
            return "break"

        # Run command in a separate thread to avoid blocking the GUI
        thread = threading.Thread(target=self._execute_command, args=(command_parts,), daemon=True)
        thread.start()

        # Start polling for output if not already doing so
        if not self.is_polling:
            self.is_polling = True
            self.after(self._POLL_INTERVAL_MS, self._poll_output)

        return "break"

    def _execute_command(self, command_parts):
        """Executes the command in a subprocess and queues the output."""
        try:
            process = subprocess.Popen(
                command_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            for line in process.stdout:
                self.output_queue.put(line)
            process.stdout.close()
            process.wait()
        except Exception as e:
            self.output_queue.put(f"Error: {e}\n")
        finally:
            # Signal that the process is finished and a new prompt is needed
            self.output_queue.put(self._PROMPT_SENTINEL)

    def _poll_output(self):
        """Polls the output queue and updates the terminal widget."""
        try:
            while True:
                line = self.output_queue.get_nowait()
                if line is self._PROMPT_SENTINEL:
                    self.add_new_prompt()
                else:
                    self.terminal_output.insert(tk.END, line)
                    self.terminal_output.see(tk.END)
        except queue.Empty:
            pass # No more items for now
        finally:
            self.after(self._POLL_INTERVAL_MS, self._poll_output)

# --- Tkinter GUI Application ---
class DockerMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Docker Monitor")
        
        # Get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        # Set geometry to cover the entire screen
        self.geometry(f"{screen_width}x{screen_height}+0+0")

        self.configure(bg='#1e2a35')

        self.log_update_idx = 0

        self.setup_styles()

        # --- Main Layout ---
        # The main split is now horizontal: Controls on the left, everything else on the right.
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Left Pane: Controls ---
        controls_frame = ttk.Labelframe(main_pane, text="Controls", width=170)
        main_pane.add(controls_frame, weight=0)

        # --- Right Pane (Vertical Split) ---
        right_pane = ttk.PanedWindow(main_pane, orient=tk.VERTICAL)
        main_pane.add(right_pane, weight=1)

        # Set the initial sash positions for a balanced layout
        self.after(100, lambda: main_pane.sashpos(0, 140))
        self.after(100, lambda: right_pane.sashpos(0, 360))

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

        # --- Widgets ---
        self.create_control_widgets(controls_frame)
        self.create_container_widgets(containers_frame)
        self.create_log_widgets(logs_frame)
        self.create_terminal_widgets(terminal_frame)

        # --- Start background tasks ---
        self.update_container_list()
        self.update_logs()

    def setup_styles(self):
        """Configures the visual style of the application."""
        self.style = ttk.Style(self)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            logging.warning("The 'clam' theme is not available, using default.")

        # --- Color Palette (Dark Theme) ---
        self.BG_COLOR = '#222831'      # Darker background
        self.FG_COLOR = '#EEEEEE'      # Light text
        self.FRAME_BG = '#393E46'      # Mid-tone for frames
        self.ACCENT_COLOR = '#00ADB5'  # Teal accent
        self.TREE_HEADER_BG = '#4A525A'  # Header background
        
        # --- General Widget Styling ---
        self.style.configure('.', background=self.BG_COLOR, foreground=self.FG_COLOR, font=('Segoe UI', 10))
        self.style.configure('TFrame', background=self.BG_COLOR)
        self.style.configure('TButton', padding=6, relief='flat', background=self.ACCENT_COLOR, font=('Segoe UI', 9, 'bold'))
        self.style.map('TButton', background=[('active', '#5dade2')])
        self.style.configure('TLabelframe', background=self.BG_COLOR, borderwidth=1, relief="solid")
        self.style.configure('TLabelframe.Label', background=self.BG_COLOR, foreground=self.FG_COLOR, font=('Segoe UI', 11, 'bold'))
        self.style.configure('Containers.TLabelframe.Label', foreground=self.ACCENT_COLOR) # Special color for container list title

        # --- Treeview Styling ---
        self.style.configure("Treeview",
            background=self.FRAME_BG,
            foreground=self.FG_COLOR,
            fieldbackground=self.FRAME_BG,
            rowheight=25,
            borderwidth=0)
        self.style.map("Treeview", background=[('selected', self.ACCENT_COLOR)])
        self.style.configure("Treeview.Heading",
            background=self.TREE_HEADER_BG,
            foreground=self.FG_COLOR,
            font=('Segoe UI', 10, 'bold'),
            relief='flat')
        self.style.map("Treeview.Heading", background=[('active', self.ACCENT_COLOR)])
        self.tree_tags_configured = False # To set up alternating row colors only once

    def create_control_widgets(self, parent):
        # --- Selected Container Section ---
        ttk.Label(parent, text="Selected Container", font=('Segoe UI', 9)).pack(pady=(10, 0), padx=10, anchor='w')
        self.selected_container_label = ttk.Label(parent, text="None", font=('Segoe UI', 10, 'bold'), foreground=self.ACCENT_COLOR)
        self.selected_container_label.pack(pady=5)

        # --- Individual Actions Section ---
        individual_actions_frame = ttk.Frame(parent)
        individual_actions_frame.pack(pady=5, padx=10, fill=tk.X)

        actions = [
            ('Stop', '#d85000'),      # Darker Orange
            ('Pause', '#d4c100'),     # Darker Yellow
            ('Unpause', '#219653'),    # Darker Green
            ('Restart', '#2471a3'),    # Darker Blue
            ('Remove', '#b80000'),     # Darker Red
        ]

        for action, color in actions:
            btn = tk.Button(
                individual_actions_frame,
                text=action,
                bg=color,
                fg='black' if color in ['#d4c100'] else 'white',
                command=lambda a=action.lower(): self.run_container_action(a)
            )
            btn.pack(fill=tk.X, pady=2)

        # --- Separator ---
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=15, padx=10)

        # --- Global Actions Section ---
        ttk.Label(parent, text="Global Actions", font=('Segoe UI', 9)).pack(pady=(0, 5), padx=10, anchor='w')

        global_actions_frame = ttk.Frame(parent)
        global_actions_frame.pack(pady=0, padx=10, fill=tk.X)

        # --- Separator ---
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=15, padx=10)


        global_actions = [
            ('Stop All', '#d85000'),
            ('Pause All', '#d4c100'),
            ('Unpause All', '#219653'),
            ('Restart All', '#2471a3'),
            ('Remove All', '#b80000')
        ]

        for action, color in global_actions:
            btn = tk.Button(
                global_actions_frame,
                text=action,
                bg=color,
                fg='black' if color in ['#d4c100'] else 'white',
                command=lambda a=action.lower().replace(' all', ''): self.run_global_action(a)
            )
            btn.pack(fill=tk.X, pady=2)

        # --- Application Control Section ---
        app_control_frame = ttk.Frame(parent)
        app_control_frame.pack(pady=0, padx=10, fill=tk.X)

        refresh_btn = tk.Button(app_control_frame, text="Refresh List", bg="#00ADB5", fg='white', command=self.force_refresh_containers)
        refresh_btn.pack(fill=tk.X, pady=2)

        config_btn = tk.Button(app_control_frame, text="Config", bg="#6c757d", fg='white', command=self.open_config_window)
        config_btn.pack(fill=tk.X, pady=2)


    def create_container_widgets(self, parent):

        # --- Container Treeview ---
        tree_frame = ttk.Frame(parent) # A frame to hold the tree and scrollbar
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        cols = ('ID', 'Name', 'Status', 'CPU (%)', 'RAM (%)')
        self.tree = ttk.Treeview(parent, columns=cols, show='headings', selectmode='browse')
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)
        self.tree.column('Name', width=200)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, in_=tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, in_=tree_frame)

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

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
            container_name = item['values'][1]
            self.selected_container_label.config(text=container_name)
        else:
            self.selected_container_label.config(text="None")

    def run_container_action(self, action):
        """Runs an action (stop, pause, etc.) on the selected container."""
        selected_items = self.tree.selection()
        if not selected_items:
            logging.warning("No container selected for action.")
            return

        item = self.tree.item(selected_items[0])
        container_name = item['values'][1]
        logging.info(f"User requested '{action}' on container '{container_name}'.")

        with docker_lock:
            try:
                container = client.containers.get(container_name)
                if action == 'remove':
                    # First stop, then forcefully remove to avoid conflicts.
                    container.stop()
                    container.remove(force=True)
                elif hasattr(container, action):
                    getattr(container, action)()
            except Exception as e:
                logging.error(f"Error during '{action}' on container '{container_name}': {e}")

    def run_global_action(self, action):
        logging.info(f"User requested '{action}' on ALL containers.")
        with docker_lock:
            try:
                containers = client.containers.list(all=True)
                for container in containers:
                    if action == 'pause' and container.status == 'running': 
                        container.pause()
                    elif action == 'unpause' and container.status == 'paused': 
                        container.unpause()
                    elif action == 'stop' and container.status == 'running': 
                        container.stop()
                    elif action == 'restart': 
                        container.restart()
                    elif action == 'remove':
                        # Forcefully remove each container after stopping.
                        container.stop()
                        container.remove(force=True)
            except Exception as e:
                logging.error(f"Error during global '{action}': {e}")
            finally:
                if action in ['stop', 'remove']:
                    threading.Thread(target=docker_cleanup, daemon=True).start()

    def force_refresh_containers(self):
        """Immediately fetches all container stats and updates the GUI tree."""
        logging.info("User requested manual container list refresh.")
        # Run the blocking Docker API calls in a separate thread
        threading.Thread(target=self._fetch_all_stats_for_refresh, daemon=True).start()

    def _fetch_all_stats_for_refresh(self):
        """
        Worker function for the manual refresh thread.
        Fetches stats and puts them in the manual_refresh_queue.
        """
        with docker_lock:
            try:
                all_containers = client.containers.list(all=True)
                stats_list = [get_container_stats(c) for c in all_containers]
                manual_refresh_queue.put(stats_list)
            except Exception as e:
                logging.error(f"Error in manual refresh thread: {e}")

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
        if not self.tree_tags_configured:
            self.tree.tag_configure('oddrow', background=self.FRAME_BG)
            self.tree.tag_configure('evenrow', background=self.BG_COLOR)
            self.tree_tags_configured = True

        current_ids = {item['id'] for item in stats_list}
        tree_items = self.tree.get_children()

        for child in tree_items:
            if self.tree.item(child)['values'][0] not in current_ids:
                self.tree.delete(child)

        for item in stats_list:
            values = (item['id'], item['name'], item['status'], item['cpu'], item['ram'])
            if self.tree.exists(item['name']):
                self.tree.item(item['name'], values=values)
            else:
                self.tree.insert('', tk.END, iid=item['name'], values=values)
        self._reapply_row_tags()

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
        """Re-applies alternating row colors to the entire tree."""
        for i, iid in enumerate(self.tree.get_children()):
            self.tree.item(iid, tags=('evenrow' if i % 2 == 0 else 'oddrow',))

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


def main():
    """Main entry point for the Docker Monitor application."""
    # Start the background monitoring thread
    monitor = threading.Thread(target=monitor_thread, daemon=True)
    monitor.start()

    # Start the Tkinter GUI
    app = DockerMonitorApp()
    app.mainloop()


if __name__ == "__main__":
    main()