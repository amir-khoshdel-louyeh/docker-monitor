"""
Container Manager Module
Handles all container-related operations including listing, actions, and information display.
"""

import logging
import threading
import tkinter as tk
from tkinter import messagebox
from docker_monitor.utils.docker_utils import (
    client,
    docker_lock,
    get_container_stats,
    docker_cleanup
)


class ContainerManager:
    """Manages Docker container operations and display."""
    
    @staticmethod
    def run_container_action(tree, action):
        """Runs an action (stop, pause, restart, remove, etc.) on the selected container.
        
        Args:
            tree: Treeview widget containing containers
            action: Action to perform (stop, start, pause, unpause, restart, remove, etc.)
        """
        selected_items = tree.selection()
        if not selected_items:
            logging.warning("No container selected for action.")
            return

        item = tree.item(selected_items[0])
        container_name = item['values'][1]
        logging.info(f"User requested '{action}' on container '{container_name}'.")

        with docker_lock:
            try:
                container = client.containers.get(container_name)
                if action == 'remove':
                    # First stop, then forcefully remove to avoid conflicts.
                    container.stop()
                    container.remove(force=True)
                    # Schedule a cleanup to reclaim resources after removal
                    from docker_monitor.utils.worker import run_in_thread
                    from docker_monitor.utils.docker_utils import docker_cleanup
                    run_in_thread(docker_cleanup, on_done=None, on_error=lambda e: logging.error(f"Cleanup failed: {e}"), tk_root=None, block=False)
                elif hasattr(container, action):
                    getattr(container, action)()
            except Exception as e:
                logging.error(f"Error during '{action}' on container '{container_name}': {e}")

    @staticmethod
    def run_global_action(action):
        """Runs an action on all containers.
        
        Args:
            action: Action to perform (stop, pause, unpause, restart, remove)
        """
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
                    from docker_monitor.utils.worker import run_in_thread
                    run_in_thread(docker_cleanup, on_done=None, on_error=lambda e: logging.error(f"Cleanup failed: {e}"), tk_root=None, block=False)

    @staticmethod
    def stop_all_containers(status_bar_callback=None, log_callback=None):
        """Stop all running containers.
        
        Args:
            status_bar_callback: Callback to update status bar (optional)
            log_callback: Callback for logging (optional)
        """
        confirm = messagebox.askyesno(
            '⚠️  Confirm Stop All', 
            'Stop ALL running containers?\n\nThis action cannot be undone.'
        )
        if not confirm:
            return
        
        logging.info("⏹️  Stopping all containers...")
        if status_bar_callback:
            status_bar_callback("🔄 Stopping containers...")
        
        def stop_all():
            try:
                containers = client.containers.list()
                stopped = 0
                for container in containers:
                    try:
                        container.stop(timeout=10)
                        stopped += 1
                        if log_callback:
                            log_callback(lambda name=container.name: logging.info(f"⏹️  Stopped: {name}"))
                    except Exception as e:
                        if log_callback:
                            log_callback(lambda name=container.name, err=e: logging.warning(f"⚠️  Failed to stop {name}: {err}"))
                
                if log_callback:
                    log_callback(lambda count=stopped: logging.info(f"✅ Stopped {count} containers"))
                if status_bar_callback:
                    status_bar_callback(f"✅ Stopped {stopped} containers")
            except Exception as e:
                logging.error(f"Error stopping all containers: {e}")
                if status_bar_callback:
                    status_bar_callback("❌ Error stopping containers")
        # Run the stop_all function in the shared worker so the UI/main thread is not blocked.
        from docker_monitor.utils.worker import run_in_thread
        run_in_thread(stop_all, on_done=None, on_error=lambda e: logging.error(f"stop_all failed: {e}"), tk_root=None, block=False)

    @staticmethod
    def apply_containers_to_tree(tree, stats_list, tree_tags_configured, bg_color, frame_bg):
        """Apply container list to tree view.
        
        Args:
            tree: Treeview widget
            stats_list: List of container stats dictionaries
            tree_tags_configured: Boolean indicating if tags are configured
            bg_color: Background color for rows
            frame_bg: Frame background color for alternating rows
            
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

        # Use names as unique identifiers (since we use name as iid)
        current_names = {item['name'] for item in stats_list}
        tree_items = tree.get_children()

        for child in tree_items:
            # child is the iid which we set to container name
            if child not in current_names:
                tree.delete(child)

        for item in stats_list:
            # Use short ID (first 12 chars) for display
            short_id = item['id'][:12] if len(item['id']) > 12 else item['id']
            values = (short_id, item['name'], item['status'], item['cpu'], item['ram'])
            if tree.exists(item['name']):
                tree.item(item['name'], values=values)
            else:
                tree.insert('', tk.END, iid=item['name'], values=values)
        
        ContainerManager.reapply_row_tags(tree)
        
        # Restore selection if it still exists
        if selected_iid and tree.exists(selected_iid):
            tree.selection_set(selected_iid)
        
        return tree_tags_configured
    
    @staticmethod
    def reapply_row_tags(tree):
        """Re-applies alternating row colors to the entire tree.
        
        Args:
            tree: Treeview widget
        """
        for i, iid in enumerate(tree.get_children()):
            tree.item(iid, tags=('evenrow' if i % 2 == 0 else 'oddrow',))

    @staticmethod
    def filter_containers(all_containers, search_text):
        """Filter containers based on search query.
        
        Args:
            all_containers: List of all container stats
            search_text: Search query string
            
        Returns:
            Filtered list of containers
        """
        if not search_text:
            return all_containers
        
        search_text = search_text.lower()
        return [
            c for c in all_containers
            if search_text in c['name'].lower() or 
               search_text in c['status'].lower() or
               search_text in c['id'].lower()
        ]

    @staticmethod
    def fetch_all_stats():
        """Fetch stats for all containers.
        
        Returns:
            List of container stats dictionaries
        """
        with docker_lock:
            try:
                all_containers = client.containers.list(all=True)
                return [get_container_stats(c) for c in all_containers]
            except Exception as e:
                logging.error(f"Error fetching container stats: {e}")
                return []

    @staticmethod
    def display_container_info(info_text, container_name, placeholder_label):
        """Display detailed information about a container.
        
        Args:
            info_text: ScrolledText widget to display info
            container_name: Name of the container
            placeholder_label: Placeholder label to hide
        """
        # Hide placeholder immediately (UI change)
        try:
            placeholder_label.pack_forget()
        except Exception:
            pass

        # Use shared worker to fetch container attrs and render in main thread
        from docker_monitor.utils.worker import run_in_thread

        def _fetch():
            with docker_lock:
                try:
                    container = client.containers.get(container_name)
                    return container.attrs
                except Exception as e:
                    # Convert NotFound into a sentinel None so the on_done
                    # renderer can show a friendly message instead of propagating
                    # exceptions back through the worker scheduling (which may
                    # fail if the Tk mainloop isn't available).
                    import docker as _docker
                    if isinstance(e, getattr(_docker.errors, 'NotFound', Exception)):
                        logging.debug(f"Container {container_name} disappeared before fetch: {e}")
                        return None
                    raise

        def _render_info(info):
            try:
                if info is None:
                    ContainerManager._show_error(info_text, f"Container '{container_name}' not found")
                    return
                info_text.config(state='normal')
                info_text.delete('1.0', tk.END)

                info_text.insert(tk.END, f"Container: {container_name}\n", 'title')
                info_text.insert(tk.END, "=" * 80 + "\n\n")

                # Basic Info Section
                info_text.insert(tk.END, "\nBASIC INFORMATION\n", 'section')
                ContainerManager._add_info_line(info_text, "ID", info.get('Id', 'N/A')[:12])
                ContainerManager._add_info_line(info_text, "Name", info.get('Name', '').lstrip('/'))
                ContainerManager._add_info_line(info_text, "Status", info.get('State', {}).get('Status', 'unknown'))
                ContainerManager._add_info_line(info_text, "Image", info.get('Config', {}).get('Image', 'N/A'))
                ContainerManager._add_info_line(info_text, "Created", info.get('Created', 'N/A'))
                ContainerManager._add_info_line(info_text, "Platform", info.get('Platform', 'N/A'))
                info_text.insert(tk.END, "\n")

                # Network Info Section
                info_text.insert(tk.END, "NETWORK INFORMATION\n", 'section')
                networks = info.get('NetworkSettings', {}).get('Networks', {})
                if networks:
                    for net_name, net_info in networks.items():
                        ContainerManager._add_info_line(info_text, f"Network", net_name)
                        ContainerManager._add_info_line(info_text, f"  \u251c\u2500 IP Address", net_info.get('IPAddress', 'N/A'))
                        ContainerManager._add_info_line(info_text, f"  \u251c\u2500 Gateway", net_info.get('Gateway', 'N/A'))
                        ContainerManager._add_info_line(info_text, f"  \u2514\u2500 MAC Address", net_info.get('MacAddress', 'N/A'))
                else:
                    info_text.insert(tk.END, "  No networks attached\n")

                # Port bindings
                ports = info.get('NetworkSettings', {}).get('Ports', {})
                if ports:
                    info_text.insert(tk.END, "\n")
                    ContainerManager._add_info_line(info_text, "Port Bindings", "")
                    for container_port, host_bindings in ports.items():
                        if host_bindings:
                            for binding in host_bindings:
                                ContainerManager._add_info_line(info_text, f"  {container_port}", f"{binding.get('HostIp', '0.0.0.0')}:{binding.get('HostPort', '')}")
                info_text.insert(tk.END, "\n")

                # Volumes Section
                info_text.insert(tk.END, "VOLUMES\n", 'section')
                mounts = info.get('Mounts', [])
                if mounts:
                    for mount in mounts:
                        mount_type = mount.get('Type', 'N/A')
                        source = mount.get('Source', 'N/A')
                        destination = mount.get('Destination', 'N/A')
                        ContainerManager._add_info_line(info_text, "Mount", f"{mount_type}")
                        ContainerManager._add_info_line(info_text, "  \u251c\u2500 Source", source)
                        ContainerManager._add_info_line(info_text, "  \u2514\u2500 Destination", destination)
                else:
                    info_text.insert(tk.END, "  No volumes mounted\n")
                info_text.insert(tk.END, "\n")

                # Environment Variables
                info_text.insert(tk.END, "ENVIRONMENT VARIABLES\n", 'section')
                env_vars = info.get('Config', {}).get('Env', [])
                if env_vars:
                    for env in env_vars[:10]:  # Limit to first 10
                        info_text.insert(tk.END, f"  {env}\n", 'value')
                    if len(env_vars) > 10:
                        info_text.insert(tk.END, f"  ... and {len(env_vars) - 10} more\n", 'value')
                else:
                    info_text.insert(tk.END, "  No environment variables\n")

                # Configure tags for styling
                info_text.tag_config('title', foreground='#00ff88', font=('Segoe UI', 14, 'bold'))
                info_text.tag_config('section', foreground='#00ADB5', font=('Segoe UI', 12, 'bold'))
                info_text.tag_config('key', foreground='#FFD700', font=('Segoe UI', 10, 'bold'))
                info_text.tag_config('value', foreground='#EEEEEE', font=('Segoe UI', 10))

                info_text.config(state='disabled')
            except Exception as e:
                logging.error(f"Error rendering container info: {e}")
                ContainerManager._show_error(info_text, f"Error rendering container information: {e}")

        def _on_error(e):
            logging.error(f"Error fetching container info: {e}")
            info_text.after(0, lambda: ContainerManager._show_error(info_text, f"Error loading container information: {e}"))

        run_in_thread(_fetch, on_done=lambda info: _render_info(info), on_error=_on_error, tk_root=info_text)

    @staticmethod
    def _show_error(info_text, message):
        info_text.config(state='normal')
        info_text.delete('1.0', tk.END)
        info_text.insert(tk.END, f"Error: {message}\n")
        info_text.config(state='disabled')
    @staticmethod
    def _add_info_line(info_text, key, value):
        """Helper to add a key-value line to info text.
        
        Args:
            info_text: ScrolledText widget
            key: Information key
            value: Information value
        """
        info_text.insert(tk.END, f"{key}: ", 'key')
        info_text.insert(tk.END, f"{value}\n", 'value')

    @staticmethod
    def copy_container_id_to_clipboard(tree, clipboard_clear, clipboard_append, update_func, copy_tooltip):
        """Copy container ID to clipboard on double-click.
        
        Args:
            tree: Treeview widget
            clipboard_clear: Function to clear clipboard
            clipboard_append: Function to append to clipboard
            update_func: Function to update the widget
            copy_tooltip: CopyTooltip instance
        """
        selected_items = tree.selection()
        if selected_items:
            item = tree.item(selected_items[0])
            container_id = item['values'][0]  # ID is the first column
            container_name = item['values'][1]  # Name is the second column
            clipboard_clear()
            clipboard_append(container_id)
            update_func()  # Required for clipboard to work
            logging.info(f"Container ID copied to clipboard: {container_id}")
            # Show professional tooltip near cursor
            copy_tooltip.show(f"Copied: {container_id}")
