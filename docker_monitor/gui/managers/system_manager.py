"""
System Manager Module
Handles Docker system operations, dashboard updates, disk usage, and system reports.
"""

import datetime
import json
import logging
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog

from docker_monitor.utils.docker_utils import client, docker_lock
from docker_monitor.utils.buffer_handler import log_buffer


class SystemManager:
    """Manager class for Docker system operations."""
    
    @staticmethod
    def update_dashboard(dash_vars):
        """
        Update dashboard statistics.
        
        Args:
            dash_vars: Dictionary with keys:
                - 'running': StringVar for running containers
                - 'stopped': StringVar for stopped containers
                - 'images': StringVar for images count
                - 'volumes': StringVar for volumes count
                - 'networks': StringVar for networks count
        """
        try:
            with docker_lock:
                containers = client.containers.list(all=True)
                running = sum(1 for c in containers if c.status == 'running')
                stopped = sum(1 for c in containers if c.status != 'running')
                
                images = client.images.list()
                volumes = client.volumes.list()
                networks = client.networks.list()
                
                dash_vars['running'].set(str(running))
                dash_vars['stopped'].set(str(stopped))
                dash_vars['images'].set(str(len(images)))
                dash_vars['volumes'].set(str(len(volumes)))
                dash_vars['networks'].set(str(len(networks)))
        except Exception as e:
            logging.error(f"❌ Error updating dashboard: {e}")
    
    @staticmethod
    def prune_system(status_bar, refresh_callback):
        """Prune all unused Docker resources."""
        confirm = messagebox.askyesno(
            '⚠️  Confirm System Prune', 
            'This will remove:\n'
            '- All stopped containers\n'
            '- All unused networks\n'
            '- All dangling images\n'
            '- All build cache\n\n'
            'Are you sure?'
        )
        if not confirm:
            return
        
        logging.info("🧹 Starting system prune...")
        status_bar.config(text="🔄 Pruning system...")
        
        def prune():
            try:
                with docker_lock:
                    result = client.containers.prune()
                status_bar.after(0, lambda: logging.info(f"✓ Removed {len(result.get('ContainersDeleted', []))} containers"))
                
                with docker_lock:
                    result = client.images.prune()
                status_bar.after(0, lambda: logging.info(f"✓ Removed {len(result.get('ImagesDeleted', []))} images"))
                
                with docker_lock:
                    result = client.networks.prune()
                status_bar.after(0, lambda: logging.info(f"✓ Removed {len(result.get('NetworksDeleted', []))} networks"))
                
                with docker_lock:
                    result = client.volumes.prune()
                status_bar.after(0, lambda: logging.info(f"✓ Removed {len(result.get('VolumesDeleted', []))} volumes"))
                
                status_bar.after(0, lambda: logging.info("✅ System prune completed!"))
                status_bar.after(0, status_bar.config, {"text": "✅ System pruned successfully"})
                status_bar.after(0, refresh_callback)
            except Exception as e:
                status_bar.after(0, lambda: logging.error(f"❌ Error: {e}"))
                status_bar.after(0, status_bar.config, {"text": f"❌ Prune failed: {e}"})
        
        threading.Thread(target=prune, daemon=True).start()
    
    @staticmethod
    def show_system_info(parent):
        """Show Docker system information in a modal window."""
        try:
            with docker_lock:
                info = client.info()
            
            win = tk.Toplevel(parent)
            win.title("Docker System Information")
            win.geometry("600x500")
            win.configure(bg='#1e2a35')
            
            txt = scrolledtext.ScrolledText(
                win, wrap=tk.WORD, bg="#1e2a35", 
                fg="#e0e0e0", font=("Consolas", 10)
            )
            txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            txt.insert(tk.END, f"🐳 Docker System Information\n")
            txt.insert(tk.END, "=" * 60 + "\n\n")
            txt.insert(tk.END, f"Docker Version: {info.get('ServerVersion', 'N/A')}\n")
            txt.insert(tk.END, f"API Version: {info.get('ApiVersion', 'N/A')}\n")
            txt.insert(tk.END, f"OS: {info.get('OperatingSystem', 'N/A')}\n")
            txt.insert(tk.END, f"Architecture: {info.get('Architecture', 'N/A')}\n")
            txt.insert(tk.END, f"CPUs: {info.get('NCPU', 'N/A')}\n")
            txt.insert(tk.END, f"Total Memory: {info.get('MemTotal', 0) / (1024**3):.2f} GB\n")
            txt.insert(tk.END, f"Storage Driver: {info.get('Driver', 'N/A')}\n")
            txt.insert(tk.END, f"Logging Driver: {info.get('LoggingDriver', 'N/A')}\n")
            txt.insert(tk.END, f"\nContainers: {info.get('Containers', 0)}\n")
            txt.insert(tk.END, f"  - Running: {info.get('ContainersRunning', 0)}\n")
            txt.insert(tk.END, f"  - Paused: {info.get('ContainersPaused', 0)}\n")
            txt.insert(tk.END, f"  - Stopped: {info.get('ContainersStopped', 0)}\n")
            txt.insert(tk.END, f"\nImages: {info.get('Images', 0)}\n")
            
            txt.config(state='disabled')
            
        except Exception as e:
            messagebox.showerror('Error', f'Failed to get system info: {e}')
    
    @staticmethod
    def refresh_docker_info(docker_info_text, status_bar):
        """Refresh Docker system information in the info text widget."""
        logging.info("🔄 Fetching Docker system info...")
        status_bar.config(text="🔄 Loading Docker info...")
        
        def fetch_info():
            try:
                with docker_lock:
                    info = client.info()
                    version = client.version()
                
                output = []
                output.append("=" * 60)
                output.append("🐳 DOCKER SYSTEM INFORMATION")
                output.append("=" * 60)
                output.append(f"\n📌 Docker Version: {version.get('Version', 'N/A')}")
                output.append(f"📌 API Version: {version.get('ApiVersion', 'N/A')}")
                output.append(f"📌 OS/Arch: {info.get('OperatingSystem', 'N/A')} / {info.get('Architecture', 'N/A')}")
                output.append(f"\n🔧 System Resources:")
                output.append(f"   • Total Memory: {info.get('MemTotal', 0) / (1024**3):.2f} GB")
                output.append(f"   • CPUs: {info.get('NCPU', 'N/A')}")
                output.append(f"\n📦 Docker Objects:")
                output.append(f"   • Containers: {info.get('Containers', 0)} ({info.get('ContainersRunning', 0)} running)")
                output.append(f"   • Images: {info.get('Images', 0)}")
                output.append(f"\n🔌 Server:")
                output.append(f"   • Server Version: {info.get('ServerVersion', 'N/A')}")
                output.append(f"   • Storage Driver: {info.get('Driver', 'N/A')}")
                output.append(f"   • Docker Root Dir: {info.get('DockerRootDir', 'N/A')}")
                output.append("\n" + "=" * 60)
                
                info_text = "\n".join(output)
                
                status_bar.after(0, lambda: SystemManager._update_text_widget(docker_info_text, info_text))
                status_bar.after(0, lambda: logging.info("✅ Info refreshed"))
                status_bar.after(0, status_bar.config, {"text": "✅ Docker info loaded"})
            except Exception as e:
                status_bar.after(0, lambda: logging.error(f"❌ Error: {e}"))
                status_bar.after(0, status_bar.config, {"text": f"❌ Error loading info"})
        
        threading.Thread(target=fetch_info, daemon=True).start()
    
    @staticmethod
    def check_disk_usage(disk_usage_text, status_bar):
        """Check Docker disk usage and update text widget."""
        logging.info("📊 Checking disk usage...")
        status_bar.config(text="📊 Checking disk usage...")
        
        def fetch_usage():
            try:
                with docker_lock:
                    df = client.df()
                
                output = []
                output.append("=" * 60)
                output.append("💽 DOCKER DISK USAGE")
                output.append("=" * 60)
                
                # Containers
                containers_size = sum(c.get('SizeRw', 0) for c in df.get('Containers', []))
                output.append(f"\n📦 CONTAINERS ({len(df.get('Containers', []))} total)")
                output.append(f"   Total Size: {containers_size / (1024**3):.2f} GB")
                
                # Images
                images = df.get('Images', [])
                images_size = sum(img.get('Size', 0) for img in images)
                output.append(f"\n🖼️  IMAGES ({len(images)} total)")
                output.append(f"   Total Size: {images_size / (1024**3):.2f} GB")
                
                # Volumes
                volumes = df.get('Volumes', [])
                volumes_size = sum(v.get('UsageData', {}).get('Size', 0) for v in volumes if v.get('UsageData'))
                output.append(f"\n💾 VOLUMES ({len(volumes)} total)")
                output.append(f"   Total Size: {volumes_size / (1024**3):.2f} GB")
                
                # Build Cache
                build_cache = df.get('BuildCache', [])
                cache_size = sum(b.get('Size', 0) for b in build_cache)
                output.append(f"\n🔨 BUILD CACHE ({len(build_cache)} entries)")
                output.append(f"   Total Size: {cache_size / (1024**3):.2f} GB")
                
                total_size = containers_size + images_size + volumes_size + cache_size
                output.append(f"\n📊 TOTAL DISK USAGE: {total_size / (1024**3):.2f} GB")
                output.append("=" * 60)
                
                usage_text = "\n".join(output)
                
                status_bar.after(0, lambda: SystemManager._update_text_widget(disk_usage_text, usage_text))
                status_bar.after(0, lambda: logging.info("✅ Disk usage loaded"))
                status_bar.after(0, status_bar.config, {"text": "✅ Disk usage checked"})
            except Exception as e:
                status_bar.after(0, lambda: logging.error(f"❌ Error: {e}"))
                status_bar.after(0, status_bar.config, {"text": f"❌ Error checking disk usage"})
        
        threading.Thread(target=fetch_usage, daemon=True).start()
    
    @staticmethod
    def _update_text_widget(text_widget, text):
        """Update a text widget with new content."""
        text_widget.delete('1.0', tk.END)
        text_widget.insert('1.0', text)
    
    @staticmethod
    def export_system_report(parent, status_bar, default_mem_limit=None, default_cpu_limit=None, 
                            auto_refresh_enabled=False, refresh_interval=None):
        """Export complete system report to a text file."""
        # Ask user for save location
        default_filename = f"docker_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=default_filename,
            title="Save System Report"
        )
        
        if not filepath:
            return
        
        logging.info(f"📄 Exporting system report to: {filepath}")
        status_bar.config(text="📄 Generating system report...")
        
        def generate_report():
            try:
                report_lines = []
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Header
                report_lines.append("=" * 80)
                report_lines.append("🐳 DOCKER SYSTEM REPORT")
                report_lines.append("=" * 80)
                report_lines.append(f"Generated: {timestamp}")
                report_lines.append(f"Application: Docker Monitor Manager")
                report_lines.append("=" * 80)
                report_lines.append("")
                
                with docker_lock:
                    # Docker System Information
                    report_lines.append("\n" + "=" * 80)
                    report_lines.append("📊 DOCKER SYSTEM INFORMATION")
                    report_lines.append("=" * 80)
                    try:
                        info = client.info()
                        version = client.version()
                        report_lines.append(f"Docker Version: {version.get('Version', 'N/A')}")
                        report_lines.append(f"API Version: {version.get('ApiVersion', 'N/A')}")
                        report_lines.append(f"OS/Arch: {info.get('OperatingSystem', 'N/A')} / {info.get('Architecture', 'N/A')}")
                        report_lines.append(f"Server Version: {info.get('ServerVersion', 'N/A')}")
                        report_lines.append(f"Storage Driver: {info.get('Driver', 'N/A')}")
                        report_lines.append(f"Logging Driver: {info.get('LoggingDriver', 'N/A')}")
                        report_lines.append(f"Docker Root Dir: {info.get('DockerRootDir', 'N/A')}")
                        report_lines.append(f"\nSystem Resources:")
                        report_lines.append(f"  Total Memory: {info.get('MemTotal', 0) / (1024**3):.2f} GB")
                        report_lines.append(f"  CPUs: {info.get('NCPU', 'N/A')}")
                        report_lines.append(f"\nDocker Objects:")
                        report_lines.append(f"  Containers: {info.get('Containers', 0)} (Running: {info.get('ContainersRunning', 0)}, Stopped: {info.get('ContainersStopped', 0)}, Paused: {info.get('ContainersPaused', 0)})")
                        report_lines.append(f"  Images: {info.get('Images', 0)}")
                    except Exception as e:
                        report_lines.append(f"Error fetching system info: {e}")
                    
                    # Containers
                    report_lines.append("\n" + "=" * 80)
                    report_lines.append("📦 CONTAINERS")
                    report_lines.append("=" * 80)
                    try:
                        containers = client.containers.list(all=True)
                        if containers:
                            for container in containers:
                                report_lines.append(f"\nContainer: {container.name}")
                                report_lines.append(f"  ID: {container.short_id}")
                                report_lines.append(f"  Status: {container.status}")
                                report_lines.append(f"  Image: {container.image.tags[0] if container.image.tags else container.image.short_id}")
                                report_lines.append(f"  Created: {container.attrs.get('Created', 'N/A')}")
                                
                                # Ports
                                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                                if ports:
                                    report_lines.append(f"  Ports: {ports}")
                                
                                # Networks
                                networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
                                if networks:
                                    report_lines.append(f"  Networks: {', '.join(networks.keys())}")
                        else:
                            report_lines.append("No containers found.")
                    except Exception as e:
                        report_lines.append(f"Error fetching containers: {e}")
                    
                    # Images
                    report_lines.append("\n" + "=" * 80)
                    report_lines.append("🖼️  IMAGES")
                    report_lines.append("=" * 80)
                    try:
                        images = client.images.list()
                        if images:
                            for img in images:
                                tags = img.tags if img.tags else ['<none>']
                                report_lines.append(f"\nImage: {', '.join(tags)}")
                                report_lines.append(f"  ID: {img.short_id}")
                                report_lines.append(f"  Size: {img.attrs.get('Size', 0) / (1024**2):.2f} MB")
                                report_lines.append(f"  Created: {img.attrs.get('Created', 'N/A')}")
                        else:
                            report_lines.append("No images found.")
                    except Exception as e:
                        report_lines.append(f"Error fetching images: {e}")
                    
                    # Networks
                    report_lines.append("\n" + "=" * 80)
                    report_lines.append("🌐 NETWORKS")
                    report_lines.append("=" * 80)
                    try:
                        networks = client.networks.list()
                        if networks:
                            for net in networks:
                                report_lines.append(f"\nNetwork: {net.name}")
                                report_lines.append(f"  ID: {net.short_id}")
                                report_lines.append(f"  Driver: {net.attrs.get('Driver', 'N/A')}")
                                report_lines.append(f"  Scope: {net.attrs.get('Scope', 'N/A')}")
                                containers_in_net = net.attrs.get('Containers', {})
                                if containers_in_net:
                                    report_lines.append(f"  Connected Containers: {len(containers_in_net)}")
                        else:
                            report_lines.append("No networks found.")
                    except Exception as e:
                        report_lines.append(f"Error fetching networks: {e}")
                    
                    # Volumes
                    report_lines.append("\n" + "=" * 80)
                    report_lines.append("💾 VOLUMES")
                    report_lines.append("=" * 80)
                    try:
                        volumes = client.volumes.list()
                        if volumes:
                            for vol in volumes:
                                report_lines.append(f"\nVolume: {vol.name}")
                                report_lines.append(f"  Driver: {vol.attrs.get('Driver', 'N/A')}")
                                report_lines.append(f"  Mountpoint: {vol.attrs.get('Mountpoint', 'N/A')}")
                                labels = vol.attrs.get('Labels', {})
                                if labels:
                                    report_lines.append(f"  Labels: {labels}")
                        else:
                            report_lines.append("No volumes found.")
                    except Exception as e:
                        report_lines.append(f"Error fetching volumes: {e}")
                    
                    # Disk Usage
                    report_lines.append("\n" + "=" * 80)
                    report_lines.append("💽 DISK USAGE")
                    report_lines.append("=" * 80)
                    try:
                        df = client.df()
                        
                        containers_size = sum(c.get('SizeRw', 0) for c in df.get('Containers', []))
                        report_lines.append(f"\nContainers: {len(df.get('Containers', []))} total")
                        report_lines.append(f"  Total Size: {containers_size / (1024**3):.2f} GB")
                        
                        images_size = sum(img.get('Size', 0) for img in df.get('Images', []))
                        report_lines.append(f"\nImages: {len(df.get('Images', []))} total")
                        report_lines.append(f"  Total Size: {images_size / (1024**3):.2f} GB")
                        
                        volumes = df.get('Volumes', [])
                        volumes_size = sum(v.get('UsageData', {}).get('Size', 0) for v in volumes if v.get('UsageData'))
                        report_lines.append(f"\nVolumes: {len(volumes)} total")
                        report_lines.append(f"  Total Size: {volumes_size / (1024**3):.2f} GB")
                        
                        build_cache = df.get('BuildCache', [])
                        cache_size = sum(b.get('Size', 0) for b in build_cache)
                        report_lines.append(f"\nBuild Cache: {len(build_cache)} entries")
                        report_lines.append(f"  Total Size: {cache_size / (1024**3):.2f} GB")
                        
                        total_size = containers_size + images_size + volumes_size + cache_size
                        report_lines.append(f"\nTOTAL DISK USAGE: {total_size / (1024**3):.2f} GB")
                    except Exception as e:
                        report_lines.append(f"Error fetching disk usage: {e}")
                
                # Application Settings
                report_lines.append("\n" + "=" * 80)
                report_lines.append("⚙️  APPLICATION SETTINGS")
                report_lines.append("=" * 80)
                if default_mem_limit:
                    report_lines.append(f"Default Memory Limit: {default_mem_limit}")
                if default_cpu_limit:
                    report_lines.append(f"Default CPU Limit: {default_cpu_limit}")
                report_lines.append(f"Auto-refresh: {'Enabled' if auto_refresh_enabled else 'Disabled'}")
                if refresh_interval:
                    report_lines.append(f"Refresh Interval: {refresh_interval} seconds")
                
                # Application Logs
                report_lines.append("\n" + "=" * 80)
                report_lines.append("📋 APPLICATION LOGS")
                report_lines.append("=" * 80)
                if log_buffer:
                    report_lines.append(f"Total log entries: {len(log_buffer)}")
                    report_lines.append("\nRecent logs:")
                    for log_entry in log_buffer:
                        report_lines.append(f"  {log_entry}")
                else:
                    report_lines.append("No logs available.")
                
                # Footer
                report_lines.append("\n" + "=" * 80)
                report_lines.append("END OF REPORT")
                report_lines.append("=" * 80)
                
                # Write to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(report_lines))
                
                status_bar.after(0, lambda: logging.info(f"✅ System report exported successfully to: {filepath}"))
                status_bar.after(0, lambda: messagebox.showinfo('Success', f'System report exported successfully!\n\nFile: {filepath}'))
                status_bar.after(0, status_bar.config, {"text": "✅ Report exported successfully"})
                
            except Exception as e:
                status_bar.after(0, lambda: logging.error(f"Failed to export system report: {e}"))
                status_bar.after(0, lambda: messagebox.showerror('Error', f'Failed to export report:\n{e}'))
                status_bar.after(0, status_bar.config, {"text": "❌ Export failed"})
        
        threading.Thread(target=generate_report, daemon=True).start()
