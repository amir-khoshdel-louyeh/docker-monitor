"""
Volume Manager Module
Handles all Docker volume-related operations.
"""

import json
import logging
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

from docker_monitor.utils.docker_utils import client, docker_lock


class VolumeManager:
    """Manager class for Docker volume operations."""
    
    @staticmethod
    def fetch_volumes():
        """Fetch all volumes from Docker."""
        with docker_lock:
            vols = client.volumes.list()
            vol_list = []
            for vol in vols:
                attrs = getattr(vol, 'attrs', {})
                vol_list.append({
                    'Name': vol.name,
                    'Driver': attrs.get('Driver', ''),
                    'Mountpoint': attrs.get('Mountpoint', ''),
                    'Labels': attrs.get('Labels', {})
                })
        return vol_list
    
    @staticmethod
    def update_volumes_tree(volumes_tree, vol_list, tags_configured, bg_color, frame_bg):
        """Update the volumes tree widget with volume data."""
        if not tags_configured:
            volumes_tree.tag_configure('oddrow', background=frame_bg)
            volumes_tree.tag_configure('evenrow', background=bg_color)
            tags_configured = True

        # Save current selection
        current_selection = volumes_tree.selection()
        selected_iid = current_selection[0] if current_selection else None

        current_names = {v['Name'] for v in vol_list}
        for child in list(volumes_tree.get_children()):
            if volumes_tree.item(child)['values'][0] not in current_names:
                volumes_tree.delete(child)

        for v in vol_list:
            labels = ','.join([f"{k}={v}" for k, v in (v.get('Labels') or {}).items()]) if v.get('Labels') else ''
            values = (v['Name'], v.get('Driver', ''), v.get('Mountpoint', ''), labels)
            iid = v['Name']
            if volumes_tree.exists(iid):
                volumes_tree.item(iid, values=values)
            else:
                volumes_tree.insert('', tk.END, iid=iid, values=values)

        for i, iid in enumerate(volumes_tree.get_children()):
            volumes_tree.item(iid, tags=('evenrow' if i % 2 == 0 else 'oddrow',))
        
        # Restore selection if it still exists
        if selected_iid and volumes_tree.exists(selected_iid):
            volumes_tree.selection_set(selected_iid)
        
        return tags_configured
    
    @staticmethod
    def filter_volumes(volumes_tree, all_volumes, search_var, bg_color, frame_bg):
        """Filter volumes based on search query."""
        search_text = search_var.get().lower()
        if not search_text:
            # Show all volumes
            VolumeManager.update_volumes_tree(
                volumes_tree, all_volumes, True, bg_color, frame_bg
            )
            return
        
        # Filter volumes
        filtered = [
            v for v in all_volumes
            if search_text in v['Name'].lower() or
               search_text in v.get('Driver', '').lower() or
               search_text in v.get('Mountpoint', '').lower()
        ]
        VolumeManager.update_volumes_tree(
            volumes_tree, filtered, True, bg_color, frame_bg
        )
    
    @staticmethod
    def remove_volume(name, update_callback):
        """Remove a volume."""
        confirm = messagebox.askyesno('Confirm Remove', f'Remove volume {name}?')
        if not confirm:
            return
        
        try:
            with docker_lock:
                vol = client.volumes.get(name)
                vol.remove()
            logging.info(f'✅ Removed volume {name}')
            update_callback()
        except Exception as e:
            logging.error(f'❌ Failed to remove volume {name}: {e}')
            messagebox.showerror('Error', f'Failed to remove volume: {str(e)}')
    
    @staticmethod
    def prune_volumes(refresh_callback, status_bar):
        """Remove unused volumes."""
        confirm = messagebox.askyesno(
            '⚠️  Confirm Volume Prune', 
            'This will permanently delete all unused volumes!\n'
            'Data cannot be recovered. Continue?'
        )
        if not confirm:
            return
        
        logging.info("🧹 Pruning unused volumes...")
        
        def prune():
            try:
                with docker_lock:
                    result = client.volumes.prune()
                count = len(result.get('VolumesDeleted', []))
                status_bar.after(0, lambda: logging.info(f"✅ Removed {count} volumes"))
                status_bar.after(0, status_bar.config, {"text": f"✅ Removed {count} volumes"})
                status_bar.after(0, refresh_callback)
            except Exception as e:
                status_bar.after(0, lambda: logging.error(f"❌ Error: {e}"))
        
            from docker_monitor.utils.worker import run_in_thread
            run_in_thread(prune, on_done=None, on_error=lambda e: status_bar.after(0, lambda: logging.error(f"Prune failed: {e}")), tk_root=None, block=True)
    
    @staticmethod
    def show_volume_inspect_modal(parent, name):
        """Show detailed inspect information for a volume in a modal window."""
        try:
            with docker_lock:
                vol = client.volumes.get(name)
                attrs = vol.attrs
            
            win = tk.Toplevel(parent)
            win.title(f'Volume: {name}')
            win.geometry('800x600')
            win.configure(bg='#222831')
            
            txt = scrolledtext.ScrolledText(
                win, width=80, height=20,
                bg='#2d2d2d', fg='#ffffff',
                insertbackground='#00ADB5',
                selectbackground='#00ADB5',
                selectforeground='#ffffff'
            )
            txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            try:
                txt.insert(tk.END, json.dumps(attrs, indent=2))
            except Exception:
                txt.insert(tk.END, str(attrs))
            
            txt.config(state='disabled')
            
        except Exception as e:
            logging.error(f'❌ Error inspecting volume {name}: {e}')
            messagebox.showerror('Error', f'Failed to inspect volume: {str(e)}')
    
    @staticmethod
    def run_volume_action(volumes_tree, action, update_callback, parent):
        """Execute a volume action."""
        if action == 'prune':
            # This will be handled separately via prune_volumes
            return
        
        sel = volumes_tree.selection()
        if not sel:
            logging.warning('⚠️ No volume selected for action.')
            messagebox.showwarning('Warning', 'Please select a volume first.')
            return
        
        name = volumes_tree.item(sel[0])['values'][0]
        
        if action == 'remove':
            VolumeManager.remove_volume(name, update_callback)
        elif action == 'inspect':
            VolumeManager.show_volume_inspect_modal(parent, name)
        else:
            logging.warning(f'⚠️ Unknown volume action: {action}')
    
    @staticmethod
    def display_volume_info(info_text, volume_name, info_placeholder_label):
        """Display detailed information about a volume in the Info tab."""
        # Hide placeholder immediately
        try:
            info_placeholder_label.pack_forget()
        except Exception:
            pass

        from docker_monitor.utils.worker import run_in_thread

        def _fetch():
            with docker_lock:
                volume = client.volumes.get(volume_name)
                return volume.attrs

        def _render_info(info):
            try:
                info_text.config(state='normal')
                info_text.delete('1.0', tk.END)

                # Title
                info_text.insert(tk.END, f"Volume: {volume_name}\n", 'title')
                info_text.insert(tk.END, "=" * 80 + "\n\n")

                # Basic Info
                info_text.insert(tk.END, "BASIC INFORMATION\n", 'section')
                VolumeManager._add_info_line(info_text, "Name", info.get('Name', 'N/A'))
                VolumeManager._add_info_line(info_text, "Driver", info.get('Driver', 'N/A'))
                VolumeManager._add_info_line(info_text, "Mountpoint", info.get('Mountpoint', 'N/A'))
                VolumeManager._add_info_line(info_text, "Created", info.get('CreatedAt', 'N/A'))
                VolumeManager._add_info_line(info_text, "Scope", info.get('Scope', 'N/A'))
                info_text.insert(tk.END, "\n")

                # Labels
                info_text.insert(tk.END, "LABELS\n", 'section')
                labels = info.get('Labels', {})
                if labels:
                    for key, value in labels.items():
                        VolumeManager._add_info_line(info_text, key, value)
                else:
                    info_text.insert(tk.END, "  No labels\n")
                info_text.insert(tk.END, "\n")

                # Options
                info_text.insert(tk.END, "OPTIONS\n", 'section')
                options = info.get('Options', {})
                if options:
                    for key, value in options.items():
                        VolumeManager._add_info_line(info_text, key, str(value))
                else:
                    info_text.insert(tk.END, "  No options\n")
                info_text.insert(tk.END, "\n")

                # Containers using this volume
                info_text.insert(tk.END, "CONTAINERS USING THIS VOLUME\n", 'section')
                with docker_lock:
                    containers = client.containers.list(all=True)
                using_containers = []
                for container in containers:
                    mounts = container.attrs.get('Mounts', [])
                    for mount in mounts:
                        if mount.get('Type') == 'volume' and mount.get('Name') == volume_name:
                            using_containers.append({
                                'name': container.name,
                                'destination': mount.get('Destination', 'N/A')
                            })

                if using_containers:
                    for c in using_containers:
                        VolumeManager._add_info_line(info_text, c['name'], f"mounted at {c['destination']}")
                else:
                    info_text.insert(tk.END, "  No containers using this volume\n")

                info_text.config(state='disabled')
            except Exception as e:
                VolumeManager._show_info_error(info_text, f"Error rendering volume info: {str(e)}")

        def _on_error(e):
            logging.error(f"Error fetching volume info: {e}")
            info_text.after(0, lambda: VolumeManager._show_info_error(info_text, f"Error fetching volume info: {str(e)}"))

        run_in_thread(_fetch, on_done=lambda info: _render_info(info), on_error=_on_error, tk_root=info_text)
    
    @staticmethod
    def _add_info_line(info_text, key, value):
        """Helper to add a formatted key-value line to info text."""
        info_text.insert(tk.END, f"  {key}: ", 'key')
        info_text.insert(tk.END, f"{value}\n", 'value')
    
    @staticmethod
    def _show_info_error(info_text, message):
        """Display an error message in the info tab."""
        info_text.config(state='normal')
        info_text.delete('1.0', tk.END)
        info_text.insert(tk.END, "⚠️ ERROR\n", 'title')
        info_text.insert(tk.END, f"\n{message}\n", 'warning')
        info_text.config(state='disabled')
    
    @staticmethod
    def copy_volume_name_to_clipboard(volumes_tree, clipboard_clear, clipboard_append, 
                                      update, copy_tooltip):
        """Copy volume name to clipboard on double-click."""
        sel = volumes_tree.selection()
        if sel:
            item = volumes_tree.item(sel[0])
            volume_name = item['values'][0]  # Name is the first column
            clipboard_clear()
            clipboard_append(volume_name)
            update()
            logging.info(f"📋 Volume name copied to clipboard: {volume_name}")
            # Show professional tooltip near cursor
            copy_tooltip.show(f"Copied: {volume_name}")
