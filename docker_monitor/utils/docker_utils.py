import docker
import time
import logging
import queue
import threading

# --- Configuration ---
CPU_LIMIT = 50.0  # %
RAM_LIMIT = 5.0   # %
CLONE_NUM = 2     # Max clones per container
SLEEP_TIME = 1    # Polling interval in seconds

# --- Docker Client and Logic ---
try:
    client = docker.from_env()
    client.ping()
    logging.info("Docker client connected successfully!")
except Exception as e:
    logging.error(f"Docker client failed to connect: {e}")
    exit(1)

# Queues for inter-thread communication
stats_queue = queue.Queue()
manual_refresh_queue = queue.Queue()  # A dedicated queue for manual refresh results
network_refresh_queue = queue.Queue()
logs_stream_queue = queue.Queue()
events_queue = queue.Queue()
docker_lock = threading.Lock()  # A lock to prevent race conditions on Docker operations


def calculate_cpu_percent(stats):
    """Calculate CPU usage percentage from Docker stats."""
    try:
        cpu_current = stats['cpu_stats']['cpu_usage']['total_usage']
        cpu_prev = stats['precpu_stats']['cpu_usage']['total_usage']
       
        system_current = stats['cpu_stats']['system_cpu_usage']
        system_prev = stats['precpu_stats']['system_cpu_usage']

        cpu_delta = cpu_current - cpu_prev
        system_delta = system_current - system_prev

        num_cpus = stats['cpu_stats'].get('online_cpus', 1)
        
        if system_delta > 0 and cpu_delta > 0:
            CPU_percent = (cpu_delta / system_delta) * num_cpus * 100.0
        else:
            CPU_percent = 0.0

        return CPU_percent
    except (KeyError, TypeError):
        pass
    return 0.0


def calculate_ram_percent(stats):
    """Calculate RAM usage percentage from Docker stats."""
    try:
        mem_usage = stats['memory_stats'].get('usage', 0)
        mem_limit = stats['memory_stats'].get('limit', 1)
        return (mem_usage / mem_limit) * 100.0
    except (KeyError, TypeError):
        pass
    return 0.0


def get_container_stats(container):
    """Get stats for a single container."""
    try:
        stats = container.stats(stream=False)

        cpu = calculate_cpu_percent(stats)
        ram = calculate_ram_percent(stats)
        return {
            'id': container.short_id,
            'name': container.name,
            'status': container.status,
            'cpu': f"{cpu:.2f}",
            'ram': f"{ram:.2f}"
        }
    except Exception:
        return {
            'id': container.short_id, 
            'name': container.name, 
            'status': 'error', 
            'cpu': '0.00', 
            'ram': '0.00'
        }


def is_clone_container(container):
    """
    Check if a container is a clone created by this application.
    Uses labels to identify clone containers reliably.
    """
    try:
        labels = container.labels or {}
        return labels.get('dmm.is_clone') == 'true' and 'dmm.parent_container' in labels
    except Exception:
        return False


def get_parent_container_name(container):
    """Get the parent container name from a clone container."""
    try:
        labels = container.labels or {}
        return labels.get('dmm.parent_container', '')
    except Exception:
        return ''


def delete_clones(container, all_containers):
    """Delete all clone containers for a given container."""
    container_name = container.name
    existing_clones = [c for c in all_containers if is_clone_container(c) and get_parent_container_name(c) == container_name]
    for clone in existing_clones:
        try:
            clone.stop()
            clone.remove()
            logging.info(f"Deleted clone container {clone.name}.")
        except Exception as e:
            logging.error(f"Failed to delete clone container {clone.name}: {e}")


def docker_cleanup():
    """Cleanup Docker resources."""
    try:
        # Use the Docker SDK for a cleaner and more robust implementation
        client.images.prune(filters={'dangling': True})  # Prune dangling images created by .commit()
        client.volumes.prune()
    except Exception as e:
        logging.error(f"An error occurred during Docker cleanup: {e}")


def scale_container(container, all_containers):
    """Scale a container by creating clones."""
    container_name = container.name
    existing_clones = [c for c in all_containers if is_clone_container(c) and get_parent_container_name(c) == container_name]

    if len(existing_clones) >= CLONE_NUM:
        logging.info(f"Max clones reached for '{container_name}'. Pausing original and deleting clones.")
        try:
            container.pause()
            logging.info(f"Paused original container '{container_name}'.")
        except Exception as e:
            logging.error(f"Failed to pause original container '{container_name}': {e}")
        delete_clones(container, all_containers)
        # Run cleanup in a separate thread to avoid blocking
        threading.Thread(target=docker_cleanup, daemon=True).start()
        return

    clone_name = f"{container_name}_clone{len(existing_clones) + 1}"
    try:
        temp_image = container.commit()
        # Create clone with labels to mark it as a clone and identify parent
        client.containers.run(
            image=temp_image.id,
            name=clone_name,
            detach=True,
            labels={
                'dmm.is_clone': 'true',
                'dmm.parent_container': container_name,
                'dmm.created_by': 'docker-monitor-manager'
            }
        )
        logging.info(f"Successfully created clone container '{clone_name}'.")
    except Exception as e:
        logging.error(f"Error creating clone container '{clone_name}': {e}")
    
    # Run cleanup in a separate thread to avoid blocking
    threading.Thread(target=docker_cleanup, daemon=True).start()


def monitor_thread():
    """Background thread for monitoring Docker containers."""
    global SLEEP_TIME

    while True:
        with docker_lock:
            try:
                all_containers = client.containers.list(all=True)
                stats_list = []
                for container in all_containers:
                    stats = get_container_stats(container)
                    stats_list.append(stats)

                    # --- Auto-scaling logic ---
                    # Only consider 'running' containers for scaling to avoid race conditions with paused ones.
                    if container.status == 'running':
                        cpu_float = float(stats['cpu'])
                        ram_float = float(stats['ram'])

                        # Only scale if it's not a clone container (check using labels, not name)
                        if (cpu_float > CPU_LIMIT or ram_float > RAM_LIMIT) and not is_clone_container(container):
                            logging.info(f"Container {container.name} overloaded (CPU: {cpu_float:.2f}%, RAM: {ram_float:.2f}%). Scaling...")
                            scale_container(container, all_containers)
                            
                # Put the entire list into the queue for the GUI to process
                stats_queue.put(stats_list)

            except Exception as e:
                logging.error(f"Error in monitor loop: {e}")
        
        time.sleep(SLEEP_TIME)


def docker_events_listener():
    """
    Background thread that listens to Docker events in real-time.
    Triggers immediate updates when containers are created, started, stopped, or removed.
    """
    logging.info("Docker events listener started")
    
    # Events we care about for immediate UI updates
    relevant_events = ['create', 'start', 'stop', 'die', 'destroy', 'pause', 'unpause', 'kill', 'restart']
    
    try:
        for event in client.events(decode=True):
            try:
                # Only process container events
                if event.get('Type') == 'container' and event.get('Action') in relevant_events:
                    event_action = event.get('Action')
                    container_name = event.get('Actor', {}).get('Attributes', {}).get('name', 'unknown')
                    
                    logging.info(f"Docker event detected: {event_action} on container '{container_name}'")
                    
                    # Trigger an immediate refresh by fetching current stats
                    with docker_lock:
                        try:
                            all_containers = client.containers.list(all=True)
                            stats_list = []
                            for container in all_containers:
                                stats = get_container_stats(container)
                                stats_list.append(stats)
                            
                            # Put the stats in the queue for immediate GUI update
                            stats_queue.put(stats_list)
                            
                        except Exception as e:
                            logging.error(f"Error processing event {event_action}: {e}")
                            
            except Exception as e:
                logging.error(f"Error handling event: {e}")
                
    except Exception as e:
        logging.error(f"Docker events listener error: {e}")
        # Restart the listener after a short delay
        time.sleep(5)
        logging.info("Restarting Docker events listener...")
        docker_events_listener()
