"""
UI Components Module
Contains UI-related utility functions and styles for Docker Monitor Manager.
"""

import tkinter as tk
from tkinter import ttk
import logging


class UIComponents:
    """Helper class containing UI component creation and styling methods."""
    
    @staticmethod
    def setup_styles(app_instance):
        """Configures the visual style of the application."""
        app_instance.style = ttk.Style(app_instance)
        try:
            app_instance.style.theme_use('clam')
        except tk.TclError:
            logging.warning("The 'clam' theme is not available, using default.")

        # --- Color Palette (Dark Theme) ---
        app_instance.BG_COLOR = '#222831'      # Darker background
        app_instance.FG_COLOR = '#EEEEEE'      # Light text
        app_instance.FRAME_BG = '#393E46'      # Mid-tone for frames
        app_instance.ACCENT_COLOR = '#00ADB5'  # Teal accent
        app_instance.TREE_HEADER_BG = '#4A525A'  # Header background
        
        # --- General Widget Styling ---
        app_instance.style.configure('.', background=app_instance.BG_COLOR, foreground=app_instance.FG_COLOR, font=('Segoe UI', 10))
        app_instance.style.configure('TFrame', background=app_instance.BG_COLOR)
        app_instance.style.configure('TButton', padding=6, relief='flat', background=app_instance.ACCENT_COLOR, font=('Segoe UI', 9, 'bold'))
        app_instance.style.map('TButton', background=[('active', '#5dade2')])
        app_instance.style.configure('TLabelframe', background=app_instance.BG_COLOR, borderwidth=1, relief="solid")
        app_instance.style.configure('TLabelframe.Label', background=app_instance.BG_COLOR, foreground=app_instance.FG_COLOR, font=('Segoe UI', 11, 'bold'))
        app_instance.style.configure('Containers.TLabelframe.Label', foreground=app_instance.ACCENT_COLOR) # Special color for container list title

        # --- Treeview Styling ---
        app_instance.style.configure("Treeview",
            background=app_instance.FRAME_BG,
            foreground=app_instance.FG_COLOR,
            fieldbackground=app_instance.FRAME_BG,
            rowheight=25,
            borderwidth=0)
        app_instance.style.map("Treeview", background=[('selected', app_instance.ACCENT_COLOR)])
        app_instance.style.configure("Treeview.Heading",
            background=app_instance.TREE_HEADER_BG,
            foreground=app_instance.FG_COLOR,
            font=('Segoe UI', 10, 'bold'),
            relief='flat')
        app_instance.style.map("Treeview.Heading", background=[('active', app_instance.ACCENT_COLOR)])
        app_instance.tree_tags_configured = False # To set up alternating row colors only once

        # --- Notebook Tab Styling ---
        app_instance.style.configure('TNotebook', background=app_instance.BG_COLOR, borderwidth=0, tabmargins=[0, 0, 0, 0])
        app_instance.style.configure('TNotebook.Tab', 
            background=app_instance.FRAME_BG,
            foreground=app_instance.FG_COLOR,
            padding=[10, 8],  # Smaller horizontal padding
            font=('Segoe UI', 9, 'bold'))  # Slightly smaller font
        app_instance.style.map('TNotebook.Tab',
            background=[('selected', app_instance.ACCENT_COLOR), ('active', '#5dade2')],
            foreground=[('selected', '#000000'), ('active', '#ffffff')])
        
        # Try to configure tab expansion through layout
        try:
            app_instance.style.layout('TNotebook.Tab', [
                ('Notebook.tab', {
                    'sticky': 'nsew',
                    'children': [
                        ('Notebook.padding', {
                            'side': 'top',
                            'sticky': 'nsew',
                            'children': [
                                ('Notebook.label', {'side': 'top', 'sticky': 'nsew'})
                            ]
                        })
                    ]
                })
            ])
        except Exception as e:
            logging.warning(f"Could not set custom tab layout: {e}")

    @staticmethod
    def create_control_button(parent, text, bg_color, command, fg_color='white', width=15):
        """Creates a styled control button.
        
        Args:
            parent: Parent widget
            text: Button text
            bg_color: Background color
            command: Command to execute on click
            fg_color: Foreground (text) color
            width: Button width in characters (default: 15)
            
        Returns:
            tk.Button: The created button
        """
        btn = tk.Button(
            parent,
            text=text,
            bg=bg_color,
            fg=fg_color,
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            cursor='hand2',
            command=command,
            padx=8,
            pady=8,
            width=width,
            activebackground=bg_color,
            activeforeground=fg_color,
            bd=0,
            highlightthickness=0
        )
        
        def on_enter(e):
            btn['bg'] = '#5dade2'
        def on_leave(e):
            btn['bg'] = bg_color
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn

    @staticmethod
    def create_stat_card(parent, label, var, color, row, col):
        """Creates a statistics card widget.
        
        Args:
            parent: Parent widget
            label: Label text for the stat
            var: tk.StringVar to hold the value
            color: Color theme for the card
            row: Grid row position
            col: Grid column position
        """
        # Modern card with gradient-like effect
        card = tk.Frame(parent, bg='#2a3f54', relief='flat', bd=0, highlightthickness=2, highlightbackground=color)
        card.grid(row=row, column=col, padx=15, pady=15, sticky='nsew', ipadx=20, ipady=15)
        
        # Make grid cells expand
        parent.grid_rowconfigure(row, weight=1)
        parent.grid_columnconfigure(col, weight=1)
        
        # Icon/Emoji at top
        icon_text = label.split()[0]  # Get emoji
        icon_label = tk.Label(
            card,
            text=icon_text,
            font=('Segoe UI', 32),
            bg='#2a3f54',
            fg=color
        )
        icon_label.pack(pady=(15, 5))
        
        # Label
        label_text = ' '.join(label.split()[1:])  # Get text without emoji
        label_widget = tk.Label(
            card,
            text=label_text,
            font=('Segoe UI', 11, 'bold'),
            bg='#2a3f54',
            fg='#b8c5d6'
        )
        label_widget.pack(pady=(0, 10))
        
        # Value with larger font
        value_widget = tk.Label(
            card,
            textvariable=var,
            font=('Segoe UI', 28, 'bold'),
            bg='#2a3f54',
            fg=color
        )
        value_widget.pack(pady=(5, 15))
        
        # Add subtle animation on hover
        def on_enter(e):
            card.config(highlightthickness=3, bg='#34495e')
            icon_label.config(bg='#34495e')
            label_widget.config(bg='#34495e')
            value_widget.config(bg='#34495e')
        
        def on_leave(e):
            card.config(highlightthickness=2, bg='#2a3f54')
            icon_label.config(bg='#2a3f54')
            label_widget.config(bg='#2a3f54')
            value_widget.config(bg='#2a3f54')
        
        card.bind('<Enter>', on_enter)
        card.bind('<Leave>', on_leave)
        icon_label.bind('<Enter>', on_enter)
        icon_label.bind('<Leave>', on_leave)
        label_widget.bind('<Enter>', on_enter)
        label_widget.bind('<Leave>', on_leave)
        value_widget.bind('<Enter>', on_enter)
        value_widget.bind('<Leave>', on_leave)

    @staticmethod
    def add_help_section(parent, title, content):
        """Adds a help section with title and content.
        
        Args:
            parent: Parent widget
            title: Section title
            content: Section content text
            
        Returns:
            title_label: The title label widget (for scroll positioning)
        """
        title_label = tk.Label(
            parent,
            text=title,
            font=('Segoe UI', 12, 'bold'),
            bg='#1e2a35',
            fg='#00ADB5',
            anchor='w'
        )
        title_label.pack(fill=tk.X, pady=(10, 5))
        
        content_label = tk.Label(
            parent,
            text=content,
            font=('Segoe UI', 10),
            bg='#1e2a35',
            fg='#EEEEEE',
            anchor='w',
            justify=tk.LEFT,
            wraplength=750
        )
        content_label.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        return title_label

    @staticmethod
    def add_info_line(info_text, key, value):
        """Adds a key-value information line to the text widget.
        
        Args:
            info_text: ScrolledText widget
            key: Information key/label
            value: Information value
        """
        info_text.insert(tk.END, f"{key}: ", "key")
        info_text.insert(tk.END, f"{value}\n", "value")

    @staticmethod
    def show_info_error(info_text, message):
        """Shows an error message in the info text widget.
        
        Args:
            info_text: ScrolledText widget
            message: Error message to display
        """
        info_text.config(state=tk.NORMAL)
        info_text.delete(1.0, tk.END)
        info_text.insert(tk.END, message, "error")
        info_text.tag_config("error", foreground="#e74c3c", font=('Segoe UI', 10))
        info_text.config(state=tk.DISABLED)

    @staticmethod
    def show_info_placeholder(info_text):
        """Shows a placeholder message in the info text widget.
        
        Args:
            info_text: ScrolledText widget
        """
        info_text.config(state=tk.NORMAL)
        info_text.delete(1.0, tk.END)
        info_text.insert(tk.END, "Select an item to view details", "placeholder")
        info_text.tag_config("placeholder", foreground="#95a5a6", font=('Segoe UI', 11, 'italic'))
        info_text.config(state=tk.DISABLED)


class MousewheelHandler:
    """Handles mousewheel scrolling for various widgets."""
    
    @staticmethod
    def bind_mousewheel(widget, target):
        """Binds mousewheel events to scroll a target widget.
        
        Args:
            widget: Widget to bind the mousewheel events to
            target: Widget to scroll (should have yview method)
        """
        def on_mousewheel(event):
            target.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def on_mousewheel_linux_up(event):
            target.yview_scroll(-1, "units")
        
        def on_mousewheel_linux_down(event):
            target.yview_scroll(1, "units")
        
        widget.bind("<MouseWheel>", on_mousewheel)
        widget.bind("<Button-4>", on_mousewheel_linux_up)
        widget.bind("<Button-5>", on_mousewheel_linux_down)
        
        # Recursively bind to all children
        for child in widget.winfo_children():
            MousewheelHandler.bind_mousewheel(child, target)
    
    @staticmethod
    def bind_canvas_mousewheel(canvas, scrollable_frame):
        """Binds mousewheel events to a canvas with smart scrolling.
        Only scrolls when content exceeds visible area.
        
        Args:
            canvas: Canvas widget to bind events to
            scrollable_frame: Frame inside the canvas
        """
        def _on_mousewheel(event):
            # Check if scrolling is needed
            if canvas.yview() != (0.0, 1.0):  # Not showing full content
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                return "break"
        
        def _on_mousewheel_linux(event):
            # Check if scrolling is needed
            if canvas.yview() != (0.0, 1.0):  # Not showing full content
                if event.num == 4:
                    canvas.yview_scroll(-3, "units")  # Increased scroll speed
                elif event.num == 5:
                    canvas.yview_scroll(3, "units")  # Increased scroll speed
                return "break"
        
        # Bind to canvas and all its children recursively
        def bind_controls_to_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_mousewheel_linux)
            widget.bind("<Button-5>", _on_mousewheel_linux)
            for child in widget.winfo_children():
                bind_controls_to_mousewheel(child)
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_mousewheel_linux)
        canvas.bind("<Button-5>", _on_mousewheel_linux)
        bind_controls_to_mousewheel(scrollable_frame)
        bind_controls_to_mousewheel(scrollable_frame)
