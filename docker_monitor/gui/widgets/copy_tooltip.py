import tkinter as tk


class CopyTooltip:
    """A professional tooltip that appears near the cursor when copying."""
    
    def __init__(self, parent):
        self.parent = parent
        self.tooltip = None
        self.fade_after_id = None
    
    def show(self, text, x=None, y=None):
        """Show tooltip at specified position or near cursor."""
        # Cancel any pending fade
        if self.fade_after_id:
            self.parent.after_cancel(self.fade_after_id)
        
        # Remove existing tooltip
        if self.tooltip:
            self.tooltip.destroy()
        
        # Get cursor position if not specified
        if x is None or y is None:
            x = self.parent.winfo_pointerx() + 10
            y = self.parent.winfo_pointery() + 10
        
        # Create tooltip window
        self.tooltip = tk.Toplevel(self.parent)
        self.tooltip.wm_overrideredirect(True)  # Remove window decorations
        self.tooltip.wm_attributes('-topmost', True)  # Always on top
        
        # Tooltip content with modern styling
        frame = tk.Frame(self.tooltip, bg='#2d2d2d', relief='flat', borderwidth=0)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Icon and text
        label = tk.Label(
            frame,
            text=f"✓ {text}",
            bg='#2d2d2d',
            fg='#4CAF50',
            font=('Segoe UI', 9, 'bold'),
            padx=12,
            pady=6
        )
        label.pack()
        
        # Position tooltip
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        # Add fade out effect
        self.fade_after_id = self.parent.after(1500, self._fade_out)
    
    def _fade_out(self):
        """Gradually fade out the tooltip."""
        if self.tooltip:
            try:
                # Quick fade out
                self.parent.after(100, self._destroy)
            except:
                pass
    
    def _destroy(self):
        """Destroy the tooltip."""
        if self.tooltip:
            try:
                self.tooltip.destroy()
                self.tooltip = None
            except:
                pass
