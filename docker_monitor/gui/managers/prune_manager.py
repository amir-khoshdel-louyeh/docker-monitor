"""
Prune Manager Module
Handles Docker resource pruning operations (containers, images, networks).
"""

import logging
import threading
from tkinter import messagebox

from docker_monitor.utils.docker_utils import client, docker_lock


class PruneManager:
    """Manager class for Docker pruning operations."""
    
    @staticmethod
    def prune_containers(status_bar, refresh_callback):
        """Remove all stopped containers."""
        confirm = messagebox.askyesno('Confirm', 'Remove all stopped containers?')
        if not confirm:
            return
        
        logging.info("🧹 Pruning stopped containers...")
        
        def prune():
            try:
                with docker_lock:
                    result = client.containers.prune()
                count = len(result.get('ContainersDeleted', []))
                status_bar.after(0, lambda: logging.info(f"✅ Removed {count} stopped containers"))
                status_bar.after(0, status_bar.config, {"text": f"✅ Removed {count} containers"})
                status_bar.after(0, refresh_callback)
            except Exception as e:
                status_bar.after(0, lambda: logging.error(f"❌ Error: {e}"))
        
        threading.Thread(target=prune, daemon=True).start()
    
    @staticmethod
    def prune_images(status_bar, refresh_callback):
        """Remove unused images."""
        confirm = messagebox.askyesno('Confirm', 'Remove all unused images?')
        if not confirm:
            return
        
        logging.info("🧹 Pruning unused images...")
        
        def prune():
            try:
                with docker_lock:
                    result = client.images.prune(filters={'dangling': False})
                count = len(result.get('ImagesDeleted', []))
                status_bar.after(0, lambda: logging.info(f"✅ Removed {count} images"))
                status_bar.after(0, status_bar.config, {"text": f"✅ Removed {count} images"})
                status_bar.after(0, refresh_callback)
            except Exception as e:
                status_bar.after(0, lambda: logging.error(f"❌ Error: {e}"))
        
        threading.Thread(target=prune, daemon=True).start()
    
    @staticmethod
    def prune_networks(status_bar, refresh_callback):
        """Remove unused networks."""
        confirm = messagebox.askyesno(
            '⚠️  Confirm Network Prune', 
            'This will remove all unused networks!\n\n'
            'Networks currently not connected to any containers will be deleted.\n'
            'Built-in networks (bridge, host, none) will not be removed.\n\n'
            'Continue?'
        )
        if not confirm:
            return
        
        logging.info("🧹 Pruning unused networks...")
        
        def prune():
            try:
                with docker_lock:
                    result = client.networks.prune()
                count = len(result.get('NetworksDeleted', []))
                status_bar.after(0, lambda: logging.info(f"✅ Removed {count} networks"))
                status_bar.after(0, status_bar.config, {"text": f"✅ Removed {count} networks"})
                status_bar.after(0, refresh_callback)
            except Exception as e:
                status_bar.after(0, lambda: logging.error(f"❌ Error: {e}"))
        
        threading.Thread(target=prune, daemon=True).start()
    
    @staticmethod
    def remove_all_stopped_containers(status_bar, refresh_callback):
        """Remove all stopped containers."""
        confirm = messagebox.askyesno(
            '⚠️  Confirm Remove All', 
            'Remove ALL stopped containers?\n\nThis action cannot be undone.'
        )
        if not confirm:
            return
        
        logging.info("🗑️  Removing stopped containers...")
        status_bar.config(text="🔄 Removing containers...")
        
        def remove_all():
            try:
                with docker_lock:
                    containers = client.containers.list(all=True, filters={'status': 'exited'})
                removed = 0
                for container in containers:
                    try:
                        container.remove()
                        removed += 1
                        status_bar.after(0, lambda name=container.name: logging.info(f"🗑️  Removed: {name}"))
                    except Exception as e:
                        status_bar.after(0, lambda name=container.name, err=e: logging.warning(f"⚠️  Failed to remove {name}: {err}"))
                
                status_bar.after(0, lambda count=removed: logging.info(f"✅ Removed {count} containers"))
                status_bar.after(0, status_bar.config, {"text": f"✅ Removed {removed} containers"})
                status_bar.after(0, refresh_callback)
            except Exception as e:
                status_bar.after(0, lambda err=e: logging.error(f"❌ Error: {err}"))
                status_bar.after(0, status_bar.config, {"text": f"❌ Error: {e}"})
        
        threading.Thread(target=remove_all, daemon=True).start()
