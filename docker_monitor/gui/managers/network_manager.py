"""
Network Manager Module
Handles all network-related operations including listing, creation, removal, and container connections.
"""

import logging
"""
Network Manager Module
Handles all network-related operations including listing, creation, removal, and container connections.
"""

import logging
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog
from docker_monitor.utils.docker_utils import client, docker_lock, network_refresh_queue


class NetworkManager:
    """Manages Docker network operations and display."""
    
    @staticmethod
    def fetch_networks():
        """Fetch all Docker networks.
        
        Returns:
            List of network dictionaries with id, name, driver, and scope
        """
        with docker_lock:
            try:
                networks = client.networks.list()
                return [
                    {
                        'id': net.id[:12],
                        'name': net.name,
                        'driver': getattr(net, 'attrs', {}).get('Driver', ''),
                        'scope': getattr(net, 'attrs', {}).get('Scope', '')
                    }
                    for net in networks
                ]
            except Exception as e:
                logging.error(f"Error fetching networks: {e}")
                return []
    
    @staticmethod
    def fetch_networks_for_refresh():
        """Fetch networks and put in refresh queue."""
        net_list = NetworkManager.fetch_networks()
        if net_list is not None:
            network_refresh_queue.put(net_list)
    
    @staticmethod
    def update_network_tree(tree, net_list, tree_tags_configured, bg_color, frame_bg):
        """Update network tree view with network list.
        
        Args:
            tree: Treeview widget
            net_list: List of network dictionaries
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
        selected_values = None
        if current_selection:
            item = tree.item(current_selection[0])
            selected_values = item['values']
        
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)
        
        # Insert networks
        for idx, net in enumerate(net_list):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            iid = tree.insert('', tk.END, values=(net['id'], net['name'], net['driver'], net['scope']), tags=(tag,))
            
            # Restore selection if this matches the previously selected item
            if selected_values and selected_values[0] == net['id']:
                tree.selection_set(iid)
        
        return tree_tags_configured
    
    @staticmethod
    def filter_networks(all_networks, search_text):
        """Filter networks based on search query.
        
        Args:
            all_networks: List of all network dictionaries
            search_text: Search query string
            
        Returns:
            Filtered list of networks
        """
        if not search_text:
            return all_networks
        
        search_text = search_text.lower()
        return [
            n for n in all_networks
            if search_text in n['name'].lower() or 
               search_text in n['driver'].lower() or
               search_text in n['id'].lower() or
               search_text in n.get('scope', '').lower()
        ]
    
    @staticmethod
    def create_network(name_callback, driver_callback, success_callback):
        """Create a new Docker network.
        
        Args:
            name_callback: Function to get network name from user
            driver_callback: Function to get driver type from user
            success_callback: Function to call on success
        """
        name = name_callback()
        if not name:
            return
        
        driver = driver_callback()
        if not driver:
            driver = 'bridge'
        
        try:
            with docker_lock:
                client.networks.create(name, driver=driver)
            logging.info(f"Created network {name} (driver={driver}).")
            if success_callback:
                success_callback()
        except Exception as e:
            logging.error(f"Failed to create network {name}: {e}")
    
    @staticmethod
    def remove_network(network_name, confirm_callback):
        """Remove a Docker network.
        
        Args:
            network_name: Name of the network to remove
            confirm_callback: Function to get confirmation from user
        """
        if not confirm_callback(f"Remove network '{network_name}'? This may disconnect containers."):
            return
        
        try:
            with docker_lock:
                net = client.networks.get(network_name)
                net.remove()
            logging.info(f"Removed network {network_name}.")
        except Exception as e:
            logging.error(f"Error removing network '{network_name}': {e}")
    
    @staticmethod
    def prune_networks(confirm_callback, status_callback):
        """Remove unused networks.
        
        Args:
            confirm_callback: Function to get confirmation
            status_callback: Function to update status
        """
        if not confirm_callback():
            return
        
        logging.info("🗑️ Pruning unused networks...")
        if status_callback:
            status_callback("🔄 Pruning networks...")
        
        def prune():
            try:
                with docker_lock:
                    result = client.networks.prune()
                    removed = result.get('NetworksDeleted', [])
                    count = len(removed) if removed else 0
                
                logging.info(f"✅ Pruned {count} networks")
                if status_callback:
                    status_callback(f"✅ Pruned {count} networks")
            except Exception as e:
                logging.error(f"Error pruning networks: {e}")
                if status_callback:
                    status_callback("❌ Error pruning networks")
        
            from docker_monitor.utils.worker import run_in_thread
            run_in_thread(prune, on_done=None, on_error=lambda e: logging.error(f"Prune failed: {e}"), tk_root=None, block=True)
    
    @staticmethod
    def get_network_info(network_name):
        """Get detailed information about a network.
        
        Args:
            network_name: Name of the network
            
        Returns:
            Dictionary with network attributes or None
        """
        try:
            with docker_lock:
                net = client.networks.get(network_name)
                return net.attrs
        except Exception as e:
            logging.error(f"Error getting network info: {e}")
            return None
    
    @staticmethod
    def display_network_info(info_text, network_name, placeholder_label):
        """Display detailed information about a network.
        
        Args:
            info_text: ScrolledText widget to display info
            network_name: Name of the network
            placeholder_label: Placeholder label to hide
        """
        try:
            # Hide placeholder
            placeholder_label.pack_forget()
            
            info = NetworkManager.get_network_info(network_name)
            if not info:
                raise Exception("Failed to retrieve network information")
            
            # Clear existing content
            info_text.config(state='normal')
            info_text.delete('1.0', tk.END)
            
            # Title
            info_text.insert(tk.END, f"Network: {network_name}\n", 'title')
            info_text.insert(tk.END, "=" * 80 + "\n\n")
            
            # Basic Info
            info_text.insert(tk.END, "🌐 BASIC INFORMATION\n", 'section')
            NetworkManager._add_info_line(info_text, "ID", info.get('Id', 'N/A')[:12])
            NetworkManager._add_info_line(info_text, "Name", info.get('Name', 'N/A'))
            NetworkManager._add_info_line(info_text, "Driver", info.get('Driver', 'N/A'))
            NetworkManager._add_info_line(info_text, "Scope", info.get('Scope', 'N/A'))
            NetworkManager._add_info_line(info_text, "Internal", str(info.get('Internal', False)))
            NetworkManager._add_info_line(info_text, "Attachable", str(info.get('Attachable', False)))
            info_text.insert(tk.END, "\n")
            
            # IPAM Configuration
            info_text.insert(tk.END, "📊 IPAM CONFIGURATION\n", 'section')
            ipam = info.get('IPAM', {})
            ipam_config = ipam.get('Config', [])
            if ipam_config:
                for config in ipam_config:
                    NetworkManager._add_info_line(info_text, "  Subnet", config.get('Subnet', 'N/A'))
                    NetworkManager._add_info_line(info_text, "  Gateway", config.get('Gateway', 'N/A'))
            else:
                info_text.insert(tk.END, "  No IPAM configuration\n")
            info_text.insert(tk.END, "\n")
            
            # Connected Containers
            info_text.insert(tk.END, "🐳 CONNECTED CONTAINERS\n", 'section')
            containers = info.get('Containers', {})
            if containers:
                for container_id, container_info in containers.items():
                    NetworkManager._add_info_line(info_text, "Container", container_info.get('Name', 'Unknown'))
                    NetworkManager._add_info_line(info_text, "  ├─ IP Address", container_info.get('IPv4Address', 'N/A'))
                    NetworkManager._add_info_line(info_text, "  └─ MAC Address", container_info.get('MacAddress', 'N/A'))
            else:
                info_text.insert(tk.END, "  No containers connected\n")
            
            # Configure tags
            info_text.tag_config('title', foreground='#00ff88', font=('Segoe UI', 14, 'bold'))
            info_text.tag_config('section', foreground='#00ADB5', font=('Segoe UI', 12, 'bold'))
            info_text.tag_config('key', foreground='#FFD700', font=('Segoe UI', 10, 'bold'))
            info_text.tag_config('value', foreground='#EEEEEE', font=('Segoe UI', 10))
            
            info_text.config(state='disabled')
            
        except Exception as e:
            logging.error(f"Error displaying network info: {e}")
            info_text.config(state='normal')
            info_text.delete('1.0', tk.END)
            info_text.insert(tk.END, f"Error loading network information:\n{str(e)}", 'error')
            info_text.tag_config('error', foreground='#e74c3c', font=('Segoe UI', 11))
            info_text.config(state='disabled')
    
    @staticmethod
    def _add_info_line(info_text, key, value):
        """Helper to add a key-value line to info text."""
        info_text.insert(tk.END, f"{key}: ", 'key')
        info_text.insert(tk.END, f"{value}\n", 'value')
    
    @staticmethod
    def copy_network_id_to_clipboard(tree, clipboard_clear, clipboard_append, update_func, copy_tooltip):
        """Copy network ID to clipboard on double-click.
        
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
            network_id = item['values'][0]  # ID is the first column
            clipboard_clear()
            clipboard_append(network_id)
            update_func()
            logging.info(f"Network ID copied to clipboard: {network_id}")
            copy_tooltip.show(f"Copied: {network_id}")
    
    @staticmethod
    def connect_container_to_network(network_name, container_name):
        """Connect a container to a network.
        
        Args:
            network_name: Name of the network
            container_name: Name of the container
            
        Returns:
            True on success, False on failure
        """
        try:
            with docker_lock:
                net = client.networks.get(network_name)
                container = client.containers.get(container_name)
                net.connect(container)
            logging.info(f"Connected container '{container_name}' to network '{network_name}'.")
            return True
        except Exception as e:
            logging.error(f"Error connecting container to network: {e}")
            return False
    
    @staticmethod
    def disconnect_container_from_network(network_name, container_name):
        """Disconnect a container from a network.
        
        Args:
            network_name: Name of the network
            container_name: Name of the container
            
        Returns:
            True on success, False on failure
        """
        try:
            with docker_lock:
                net = client.networks.get(network_name)
                container = client.containers.get(container_name)
                net.disconnect(container)
            logging.info(f"Disconnected container '{container_name}' from network '{network_name}'.")
            return True
        except Exception as e:
            logging.error(f"Error disconnecting container from network: {e}")
            return False
    
    @staticmethod
    def get_all_containers():
        """Get all Docker containers.
        
        Returns:
            List of container objects
        """
        try:
            with docker_lock:
                return client.containers.list(all=True)
        except Exception as e:
            logging.error(f"Error fetching containers: {e}")
            return []
    
    @staticmethod
    def get_connected_containers(network_name):
        """Get containers connected to a specific network.
        
        Args:
            network_name: Name of the network
            
        Returns:
            List of container objects
        """
        try:
            with docker_lock:
                net = client.networks.get(network_name)
                container_info = net.attrs.get('Containers', {})
                if not container_info:
                    return []
                
                # Get actual container objects
                connected = []
                for container_id in container_info.keys():
                    try:
                        container = client.containers.get(container_id)
                        connected.append(container)
                    except:
                        pass
                return connected
        except Exception as e:
            logging.error(f"Error getting connected containers: {e}")
            return []
