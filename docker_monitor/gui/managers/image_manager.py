"""
Image Manager Module
Handles all image-related operations including listing, pulling, removing, and information display.
"""

import logging
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
import json
from docker_monitor.utils.docker_utils import client, docker_lock


class ImageManager:
    """Manages Docker image operations and display."""
    
    @staticmethod
    def fetch_images():
        """Fetch all Docker images.
        
        Returns:
            List of image dictionaries with id, repo_tags, size, and created
        """
        with docker_lock:
            try:
                images = client.images.list()
                return [
                    {
                        'id': im.id,
                        'repo_tags': im.tags,
                        'size': f"{getattr(im, 'attrs', {}).get('Size', 0)}",
                        'created': getattr(im, 'attrs', {}).get('Created', '')
                    }
                    for im in images
                ]
            except Exception as e:
                logging.error(f"Error fetching images: {e}")
                return []
    
    @staticmethod
    def update_images_tree(tree, img_list, tree_tags_configured, bg_color, frame_bg):
        """Update images tree view with image list.
        
        Args:
            tree: Treeview widget
            img_list: List of image dictionaries
            tree_tags_configured: Boolean indicating if tags are configured
            bg_color: Background color
            frame_bg: Frame background color
            
        Returns:
            Boolean indicating if tags were configured
        """
        if not tree_tags_configured:
            tree.tag_configure('oddrow', background=frame_bg)
            tree.tag_configure('evenrow', background=bg_color)
            tree_tags_configured = True

        # Save current selection
        current_selection = tree.selection()
        selected_iid = current_selection[0] if current_selection else None

        # Use short IDs as unique identifiers
        current_short_ids = {i['id'][:12] for i in img_list}
        for child in list(tree.get_children()):
            if child not in current_short_ids:
                tree.delete(child)

        for img in img_list:
            short_id = img['id'][:12]
            repo = ','.join(img.get('repo_tags') or [])
            values = (short_id, repo, img.get('size', ''), img.get('created', ''))
            if tree.exists(short_id):
                tree.item(short_id, values=values)
            else:
                tree.insert('', tk.END, iid=short_id, values=values)

        for i, iid in enumerate(tree.get_children()):
            tree.item(iid, tags=('evenrow' if i % 2 == 0 else 'oddrow',))
        
        # Restore selection if it still exists
        if selected_iid and tree.exists(selected_iid):
            tree.selection_set(selected_iid)
        
        return tree_tags_configured
    
    @staticmethod
    def filter_images(all_images, search_text):
        """Filter images based on search query.
        
        Args:
            all_images: List of all image dictionaries
            search_text: Search query string
            
        Returns:
            Filtered list of images
        """
        if not search_text:
            return all_images
        
        search_text = search_text.lower()
        return [
            img for img in all_images
            if search_text in img['id'].lower() or
               search_text in ','.join(img.get('repo_tags', [])).lower()
        ]
    
    @staticmethod
    def remove_image(image_id, confirm_callback):
        """Remove a Docker image.
        
        Args:
            image_id: ID of the image to remove
            confirm_callback: Function to get confirmation from user
            
        Returns:
            True on success, False on failure
        """
        if not confirm_callback(f'Remove image {image_id}?'):
            return False
        
        try:
            with docker_lock:
                client.images.remove(image_id, force=True)
            logging.info(f"Removed image {image_id}")
            return True
        except Exception as e:
            logging.error(f'Error removing image: {e}')
            return False
    
    @staticmethod
    def pull_image(repo, success_callback=None):
        """Pull a Docker image.
        
        Args:
            repo: Repository name (e.g., 'nginx:latest')
            success_callback: Function to call on success
        """
        try:
            with docker_lock:
                client.images.pull(repo)
            logging.info(f'Pulled image {repo}')
            if success_callback:
                success_callback()
        except Exception as e:
            logging.error(f'Failed to pull image {repo}: {e}')
    
    @staticmethod
    def prune_images(confirm_callback, status_callback):
        """Remove unused images.
        
        Args:
            confirm_callback: Function to get confirmation
            status_callback: Function to update status
        """
        if not confirm_callback():
            return
        
        logging.info("🗑️  Pruning unused images...")
        if status_callback:
            status_callback("🔄 Pruning images...")
        
        def prune():
            try:
                with docker_lock:
                    result = client.images.prune(filters={'dangling': False})
                    deleted = result.get('ImagesDeleted', [])
                    count = len(deleted) if deleted else 0
                    space = result.get('SpaceReclaimed', 0)
                
                logging.info(f"✅ Pruned {count} images, reclaimed {space / (1024**2):.2f} MB")
                if status_callback:
                    status_callback(f"✅ Pruned {count} images")
            except Exception as e:
                logging.error(f"Error pruning images: {e}")
                if status_callback:
                    status_callback("❌ Error pruning images")
        
        threading.Thread(target=prune, daemon=True).start()
    
    @staticmethod
    def display_image_info(info_text, image_id, placeholder_label):
        """Display detailed information about an image.
        
        Args:
            info_text: ScrolledText widget to display info
            image_id: ID of the image
            placeholder_label: Placeholder label to hide
        """
        try:
            # Hide placeholder
            placeholder_label.pack_forget()
            
            with docker_lock:
                image = client.images.get(image_id)
                info = image.attrs
            
            # Clear existing content
            info_text.config(state='normal')
            info_text.delete('1.0', tk.END)
            
            # Title
            tags = info.get('RepoTags', ['<none>'])
            info_text.insert(tk.END, f"Image: {tags[0] if tags else '<none>'}\n", 'title')
            info_text.insert(tk.END, "=" * 80 + "\n\n")
            
            # Basic Info
            info_text.insert(tk.END, "🖼️ BASIC INFORMATION\n", 'section')
            ImageManager._add_info_line(info_text, "ID", info.get('Id', 'N/A').replace('sha256:', '')[:12])
            ImageManager._add_info_line(info_text, "Tags", ', '.join(info.get('RepoTags', ['<none>'])))
            ImageManager._add_info_line(info_text, "Size", f"{info.get('Size', 0) / (1024**2):.2f} MB")
            ImageManager._add_info_line(info_text, "Created", info.get('Created', 'N/A'))
            ImageManager._add_info_line(info_text, "Architecture", info.get('Architecture', 'N/A'))
            ImageManager._add_info_line(info_text, "OS", info.get('Os', 'N/A'))
            info_text.insert(tk.END, "\n")
            
            # Container Config
            info_text.insert(tk.END, "🔧 CONTAINER CONFIGURATION\n", 'section')
            config = info.get('Config', {})
            ImageManager._add_info_line(info_text, "User", config.get('User', 'root') or 'root')
            ImageManager._add_info_line(info_text, "Working Dir", config.get('WorkingDir', '/') or '/')
            
            # Exposed Ports
            exposed = config.get('ExposedPorts', {})
            if exposed:
                ImageManager._add_info_line(info_text, "Exposed Ports", ', '.join(exposed.keys()))
            
            # Entrypoint and CMD
            entrypoint = config.get('Entrypoint', [])
            if entrypoint:
                ImageManager._add_info_line(info_text, "Entrypoint", ' '.join(entrypoint))
            cmd = config.get('Cmd', [])
            if cmd:
                ImageManager._add_info_line(info_text, "Cmd", ' '.join(cmd))
            info_text.insert(tk.END, "\n")
            
            # Environment
            info_text.insert(tk.END, "🌍 ENVIRONMENT\n", 'section')
            env = config.get('Env', [])
            if env:
                for e in env[:10]:
                    info_text.insert(tk.END, f"  {e}\n")
                if len(env) > 10:
                    info_text.insert(tk.END, f"  ... and {len(env) - 10} more\n")
            else:
                info_text.insert(tk.END, "  No environment variables\n")
            info_text.insert(tk.END, "\n")
            
            # Containers using this image
            info_text.insert(tk.END, "📦 CONTAINERS USING THIS IMAGE\n", 'section')
            with docker_lock:
                containers = client.containers.list(all=True, filters={'ancestor': image_id})
            if containers:
                for container in containers:
                    ImageManager._add_info_line(info_text, container.name, container.status)
            else:
                info_text.insert(tk.END, "  No containers using this image\n")
            
            # Configure tags
            info_text.tag_config('title', foreground='#00ff88', font=('Segoe UI', 14, 'bold'))
            info_text.tag_config('section', foreground='#00ADB5', font=('Segoe UI', 12, 'bold'))
            info_text.tag_config('key', foreground='#FFD700', font=('Segoe UI', 10, 'bold'))
            info_text.tag_config('value', foreground='#EEEEEE', font=('Segoe UI', 10))
            
            info_text.config(state='disabled')
            
        except Exception as e:
            logging.error(f"Error displaying image info: {e}")
            info_text.config(state='normal')
            info_text.delete('1.0', tk.END)
            info_text.insert(tk.END, f"Error loading image information:\n{str(e)}", 'error')
            info_text.tag_config('error', foreground='#e74c3c', font=('Segoe UI', 11))
            info_text.config(state='disabled')
    
    @staticmethod
    def _add_info_line(info_text, key, value):
        """Helper to add a key-value line to info text."""
        info_text.insert(tk.END, f"{key}: ", 'key')
        info_text.insert(tk.END, f"{value}\n", 'value')
    
    @staticmethod
    def show_image_inspect_modal(parent, image_id):
        """Show image inspect modal with JSON data.
        
        Args:
            parent: Parent window
            image_id: ID of the image
        """
        try:
            with docker_lock:
                img = client.images.get(image_id)
                attrs = img.attrs
            
            win = tk.Toplevel(parent)
            win.title(f'Image: {image_id}')
            win.geometry("800x600")
            
            txt = scrolledtext.ScrolledText(win, width=80, height=30, bg='#2a3a4a', fg='#ffffff')
            txt.pack(fill=tk.BOTH, expand=True)
            txt.insert(tk.END, json.dumps(attrs, indent=2))
            txt.config(state='disabled')
        except Exception as e:
            logging.error(f'Error showing image inspect: {e}')
    
    @staticmethod
    def copy_image_id_to_clipboard(tree, clipboard_clear, clipboard_append, update_func, copy_tooltip):
        """Copy image ID to clipboard on double-click.
        
        Args:
            tree: Treeview widget
            clipboard_clear: Function to clear clipboard
            clipboard_append: Function to append to clipboard
            update_func: Function to update the widget
            copy_tooltip: CopyTooltip instance
        """
        selected = tree.selection()
        if selected:
            item = tree.item(selected[0])
            image_id = item['values'][0]  # ID is the first column
            clipboard_clear()
            clipboard_append(image_id)
            update_func()
            logging.info(f"Image ID copied to clipboard: {image_id}")
            copy_tooltip.show(f"Copied: {image_id}")
