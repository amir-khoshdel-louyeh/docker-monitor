import tkinter as tk
import queue
import subprocess
import threading
import logging


class DockerTerminal(tk.Frame):
    """Docker Terminal Widget - A terminal emulator for Docker commands."""
    
    # A sentinel object to signal when to add a new prompt
    _PROMPT_SENTINEL = object()
    _POLL_INTERVAL_MS = 100

    def __init__(self, master, **kwargs):
        super().__init__(master)

        # Create a frame for terminal with scrollbar
        terminal_frame = tk.Frame(self)
        terminal_frame.pack(expand=True, fill=tk.BOTH)

        # Add scrollbar
        scrollbar = tk.Scrollbar(terminal_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # The internal Text widget receives styling arguments from the parent
        self.terminal_output = tk.Text(terminal_frame, yscrollcommand=scrollbar.set, **kwargs)
        self.terminal_output.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        scrollbar.config(command=self.terminal_output.yview)

        # --- Event Bindings ---
        self.terminal_output.bind("<Return>", self.run_terminal_command)
        self.terminal_output.bind("<Key>", self.handle_key_press)
        self.terminal_output.bind("<Up>", self.handle_history_up)
        self.terminal_output.bind("<Down>", self.handle_history_down)
        self.terminal_output.bind("<Home>", self.handle_home)
        self.terminal_output.bind("<End>", self.handle_end)
        self.terminal_output.bind("<Control-l>", self.handle_clear)
        self.terminal_output.bind("<Control-L>", self.handle_clear)
        self.terminal_output.bind("<Control-c>", self.handle_copy)
        self.terminal_output.bind("<Control-C>", self.handle_copy)
        self.terminal_output.bind("<BackSpace>", self.handle_backspace)
        self.terminal_output.bind("<Delete>", self.handle_delete)
        self.terminal_output.bind("<Left>", self.handle_left_arrow)
        self.terminal_output.bind("<Tab>", self.handle_tab_completion)
        
        # Mouse wheel scrolling
        self.terminal_output.bind("<MouseWheel>", self._on_mousewheel)
        self.terminal_output.bind("<Button-4>", self._on_mousewheel_linux_up)
        self.terminal_output.bind("<Button-5>", self._on_mousewheel_linux_down)

        # --- State Management ---
        self.command_history = []
        self.history_index = 0
        self.output_queue = queue.Queue()
        self.is_polling = False
        self.current_input = ""  # Store current input when navigating history

        # Docker commands for tab completion
        self.docker_commands = [
            'docker ps', 'docker images', 'docker pull', 'docker run', 'docker stop',
            'docker start', 'docker restart', 'docker rm', 'docker rmi', 'docker logs',
            'docker exec', 'docker inspect', 'docker network', 'docker volume',
            'docker build', 'docker commit', 'docker cp', 'docker create', 'docker diff',
            'docker events', 'docker export', 'docker history', 'docker import',
            'docker info', 'docker kill', 'docker load', 'docker login', 'docker logout',
            'docker pause', 'docker unpause', 'docker port', 'docker push', 'docker rename',
            'docker save', 'docker search', 'docker stats', 'docker tag', 'docker top',
            'docker unpause', 'docker update', 'docker version', 'docker wait',
            'docker container', 'docker image', 'docker network ls', 'docker volume ls',
            'docker system', 'docker system prune', 'docker compose'
        ]

        # Configure tags for colored output
        self.terminal_output.tag_config('error_tag', foreground='#e74c3c')
        self.terminal_output.tag_config('success_tag', foreground='#2ecc71')
        self.terminal_output.tag_config('warning_tag', foreground='#f39c12')
        self.terminal_output.tag_config('info_tag', foreground='#3498db')
        self.terminal_output.tag_config('prompt_tag', foreground='#00ff88', font=('Consolas', 10, 'bold'))
        self.terminal_output.tag_config('command_tag', foreground='#ffffff', font=('Consolas', 10))
        self.terminal_output.tag_config('readonly', foreground='#aaaaaa')

        # Add welcome message
        welcome_msg = "🐳 Docker Terminal - Type 'docker' commands or 'clear' to clear screen\n"
        welcome_msg += "💡 Use Up/Down arrows for history, Tab for completion, Ctrl+L to clear\n"
        welcome_msg += "─" * 70 + "\n"
        self.terminal_output.insert("1.0", welcome_msg, 'info_tag')

        # Add the initial prompt
        self.add_new_prompt()

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling on Windows/Mac."""
        self.terminal_output.yview_scroll(int(-1*(event.delta/120)), "units")
        return "break"
    
    def _on_mousewheel_linux_up(self, event):
        """Handle mouse wheel scrolling on Linux (scroll up)."""
        self.terminal_output.yview_scroll(-1, "units")
        return "break"
    
    def _on_mousewheel_linux_down(self, event):
        """Handle mouse wheel scrolling on Linux (scroll down)."""
        self.terminal_output.yview_scroll(1, "units")
        return "break"

    def handle_home(self, event):
        """Move cursor to start of input (after prompt)."""
        self.terminal_output.mark_set(tk.INSERT, "input_start")
        return "break"
    
    def handle_end(self, event):
        """Move cursor to end of input."""
        self.terminal_output.mark_set(tk.INSERT, tk.END + "-1c")
        return "break"
    
    def handle_clear(self, event):
        """Clear terminal with Ctrl+L."""
        self.terminal_output.delete("1.0", tk.END)
        self.add_new_prompt()
        return "break"
    
    def handle_copy(self, event):
        """Handle Ctrl+C for copying selected text."""
        try:
            selected_text = self.terminal_output.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            return "break"
        except tk.TclError:
            # No selection, do nothing
            return "break"
    
    def handle_backspace(self, event):
        """Prevent backspace from deleting prompt or previous output."""
        if self.terminal_output.index(tk.INSERT) <= self.terminal_output.index("input_start"):
            return "break"
        return None  # Allow default behavior
    
    def handle_delete(self, event):
        """Prevent delete from removing text after cursor if we're at the boundary."""
        if self.terminal_output.index(tk.INSERT) < self.terminal_output.index("input_start"):
            return "break"
        return None  # Allow default behavior
    
    def handle_left_arrow(self, event):
        """Prevent cursor from going before the prompt."""
        if self.terminal_output.index(tk.INSERT) <= self.terminal_output.index("input_start"):
            return "break"
        return None  # Allow default behavior

    def handle_tab_completion(self, event):
        """Provide tab completion for docker commands."""
        current_text = self.terminal_output.get("input_start", tk.END).strip()
        
        if not current_text:
            return "break"
        
        # Find matching commands
        matches = [cmd for cmd in self.docker_commands if cmd.startswith(current_text)]
        
        if len(matches) == 1:
            # Single match - complete it
            self.terminal_output.delete("input_start", tk.END)
            self.terminal_output.insert(tk.END, matches[0])
        elif len(matches) > 1:
            # Multiple matches - show them
            self.terminal_output.insert(tk.END, "\n")
            for match in matches:
                self.terminal_output.insert(tk.END, f"  {match}\n", 'info_tag')
            self.add_new_prompt()
            self.terminal_output.insert(tk.END, current_text)
        
        return "break"

    def add_new_prompt(self):
        """Adds a new input prompt to the terminal."""
        # Ensure there's a newline before the prompt, unless it's the very first line
        current_content = self.terminal_output.get("1.0", tk.END)
        if current_content.strip() and not current_content.endswith('\n'):
            self.terminal_output.insert(tk.END, "\n")

        self.terminal_output.insert(tk.END, "$ ", 'prompt_tag')
        self.terminal_output.mark_set("input_start", "end-2c") # Mark start of user input
        self.terminal_output.mark_gravity("input_start", tk.LEFT)
        self.terminal_output.see(tk.END)

    def handle_key_press(self, event):
        """Prevents deletion of the prompt or text before it."""
        # Allow specific control keys
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Home', 'End', 'BackSpace', 'Delete', 'Tab'):
            return None  # Let specific handlers deal with these
        
        # Block Control key combinations (except those we handle separately)
        if event.state & 0x4:  # Control key is pressed
            return None  # Let other handlers deal with it
        
        # If cursor is before input_start, move it to the end
        if self.terminal_output.index(tk.INSERT) < self.terminal_output.index("input_start"):
            if event.char and event.char.isprintable():
                self.terminal_output.mark_set(tk.INSERT, tk.END)
            else:
                return "break"
        
        return None  # Allow default behavior for printable characters

    def handle_history_up(self, event):
        """Navigate to previous command in history."""
        if not self.command_history:
            return "break"

        # Save current input if at the end of history
        if self.history_index == len(self.command_history):
            self.current_input = self.terminal_output.get("input_start", tk.END).strip()

        self.history_index = max(0, self.history_index - 1)

        # Clear current input and show history item
        self.terminal_output.delete("input_start", tk.END)
        self.terminal_output.insert(tk.END, self.command_history[self.history_index])

        return "break"

    def handle_history_down(self, event):
        """Navigate to next command in history."""
        if not self.command_history:
            return "break"

        self.history_index = min(len(self.command_history), self.history_index + 1)

        # Clear current input
        self.terminal_output.delete("input_start", tk.END)

        # Show history item or restore current input if at the end
        if self.history_index < len(self.command_history):
            self.terminal_output.insert(tk.END, self.command_history[self.history_index])
        else:
            self.terminal_output.insert(tk.END, self.current_input)

        return "break"

    def run_terminal_command(self, event):
        command_str = self.terminal_output.get("input_start", tk.END).strip()

        # Move to a new line and mark the command as readonly
        self.terminal_output.insert(tk.END, "\n")
        
        # Make the entered command readonly by removing the input_start mark
        self.terminal_output.mark_unset("input_start")

        if not command_str:
            self.add_new_prompt()
            return "break"

        # Add to history and reset index
        if command_str not in self.command_history or self.command_history[-1] != command_str:
            self.command_history.append(command_str)
        self.history_index = len(self.command_history)
        self.current_input = ""

        # Handle 'clear' command locally in the GUI
        if command_str.lower() == "clear":
            self.terminal_output.delete("1.0", tk.END)
            self.add_new_prompt()
            return "break"

        
        # Security: Only allow 'docker' commands
        command_parts = command_str.split()
        if not command_parts or command_parts[0] != "docker":
            msg = "❌ Security Error: Only 'docker' commands are allowed.\n"
            logging.warning(msg.strip())
            self.terminal_output.insert(tk.END, msg, 'error_tag')
            self.add_new_prompt()
            return "break"

        # Run command in a separate thread to avoid blocking the GUI
        from docker_monitor.utils.worker import run_in_thread
        run_in_thread(lambda: self._execute_command(command_parts), on_done=None, on_error=lambda e: logging.error(f"Terminal command failed: {e}"), tk_root=None, block=False)

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
            self.output_queue.put(f"❌ Error: {e}\n")
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
