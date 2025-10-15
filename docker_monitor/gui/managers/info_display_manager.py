"""
Info Display Manager Module
Handles Info Tab display operations and helper functions.
"""

import tkinter as tk


class InfoDisplayManager:
    """Manager class for Info Tab display operations."""
    
    @staticmethod
    def add_info_line(info_text, key, value):
        """Helper to add a formatted key-value line to info text."""
        info_text.insert(tk.END, f"  {key}: ", 'key')
        info_text.insert(tk.END, f"{value}\n", 'value')
    
    @staticmethod
    def show_info_error(info_text, message):
        """Display an error message in the info tab."""
        info_text.config(state='normal')
        info_text.delete('1.0', tk.END)
        info_text.insert(tk.END, "⚠️ ERROR\n", 'title')
        info_text.insert(tk.END, f"\n{message}\n", 'warning')
        info_text.config(state='disabled')
    
    @staticmethod
    def show_info_placeholder(info_text, info_placeholder_label):
        """Show placeholder message in info tab when nothing is selected."""
        info_text.config(state='normal')
        info_text.delete('1.0', tk.END)
        info_text.config(state='disabled')
        info_placeholder_label.pack(pady=20)
    
    @staticmethod
    def update_text_widget(text_widget, text):
        """Update a text widget with new content."""
        text_widget.delete('1.0', tk.END)
        text_widget.insert('1.0', text)
