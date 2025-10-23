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
# Feature flags / policies
# By default disable automatic scaling to avoid unexpected container creation
# unless explicitly enabled by the user in settings/UI.
AUTO_SCALE_ENABLED = True

# Only react to events for containers that the app created (label) or that
# match this name prefix. This prevents the GUI from chasing external
# test harness containers unless you opt in.
APP_CONTAINER_NAME_PREFIX = 'dmm-'
APP_CREATED_BY_LABEL = 'docker-monitor-manager'

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
        # Prune stopped containers, dangling images, unused volumes and networks
        try:
            containers_result = client.containers.prune()
            logging.info(f"Pruned containers: {containers_result.get('ContainersDeleted')}")
        except Exception:
            logging.debug("No stopped containers to prune or prune failed")

        try:
            images_result = client.images.prune(filters={'dangling': True})  # Prune dangling images
            logging.info(f"Pruned images: {images_result.get('ImagesDeleted')}, reclaimed={images_result.get('SpaceReclaimed')}")
        except Exception:
            logging.debug("Image prune failed")

        try:
            volumes_result = client.volumes.prune()
            logging.info(f"Pruned volumes: {volumes_result.get('VolumesDeleted')}")
        except Exception:
            logging.debug("Volume prune failed")

        try:
            networks_result = client.networks.prune()
            logging.info(f"Pruned networks: {networks_result.get('NetworksDeleted')}")
        except Exception:
            logging.debug("Network prune failed")
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
        # Schedule cleanup via shared worker to avoid raw thread storms
        from docker_monitor.utils.worker import run_in_thread
        run_in_thread(docker_cleanup, on_done=None, on_error=lambda e: logging.error(f"Cleanup failed: {e}"), tk_root=None, block=False)
        return

    clone_name = f"{container_name}_clone{len(existing_clones) + 1}"
    # If auto-scaling is disabled, do not create clones automatically.
    if not AUTO_SCALE_ENABLED:
        logging.info(f"Auto-scaling is disabled; skipping clone creation for '{container_name}'")
        return

    # IMPORTANT: automatic clone creation was used for testing and has been
    # removed to ensure we never start containers without explicit user
    # consent. If you need cloning in the future, implement an explicit
    # user-driven action in the UI and call a well-audited helper instead.
    logging.info(f"Auto-clone creation disabled by policy; skipping clone for '{container_name}'.")
    return


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
                # Only process container events and only the actions we care about
                if event.get('Type') != 'container' or event.get('Action') not in relevant_events:
                    continue

                event_action = event.get('Action')
                attrs = event.get('Actor', {}).get('Attributes', {}) or {}
                container_name = attrs.get('name', 'unknown')

                # Determine whether this container was created by this app
                created_by = attrs.get('dmm.created_by')
                is_app_container = (created_by == APP_CREATED_BY_LABEL) or (
                    isinstance(container_name, str) and container_name.startswith(APP_CONTAINER_NAME_PREFIX)
                )

                if not is_app_container:
                    # External containers: keep noise at DEBUG level and ignore their
                    # events to avoid triggering immediate GUI updates or destructive
                    # reactions.
                    logging.debug(f"External Docker event ignored: {event_action} on '{container_name}'")
                    continue

                logging.info(f"Docker event detected: {event_action} on container '{container_name}'")

                # For some rapid create/start/destroy sequences the SDK may return
                # a NotFound when trying to inspect a container that already went
                # away. To reduce noisy 404 logs and avoid transient race errors,
                # sleep a tiny amount for create/start events before listing.
                if event_action in ('create', 'start'):
                    # short debounce to let the container settle
                    time.sleep(0.05)

                # Trigger an immediate refresh by fetching current stats for app containers only
                with docker_lock:
                    try:
                        all_containers = client.containers.list(all=True)
                        stats_list = []
                        for container in all_containers:
                            try:
                                stats = get_container_stats(container)
                                stats_list.append(stats)
                            except docker.errors.NotFound:
                                # Container disappeared between list and inspect - expected
                                logging.debug(f"Container disappeared before stats could be read: {container.name}")
                            except Exception as e:
                                logging.error(f"Error getting stats for {getattr(container, 'name', container.short_id)}: {e}")

                        # Put the stats in the queue for immediate GUI update
                        stats_queue.put(stats_list)

                        # If the container was destroyed, schedule cleanup to free resources
                        if event_action == 'destroy':
                            from docker_monitor.utils.worker import run_in_thread
                            run_in_thread(docker_cleanup, on_done=None, on_error=lambda e: logging.error(f"Cleanup failed: {e}"), tk_root=None, block=False)

                    except docker.errors.NotFound as e:
                        # This can happen if a specific container referenced in the
                        # SDK query was removed concurrently. Treat as debug-worthy
                        # rather than an error to avoid alarming logs for races.
                        logging.debug(f"NotFound while processing event {event_action}: {e}")
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
