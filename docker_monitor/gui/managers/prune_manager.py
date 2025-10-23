"""Prune manager — schedule heavy prune operations in processes.

This module uses the `process_worker` to run heavy docker CLI commands in
separate processes, avoiding worker thread exhaustion and keeping the UI
responsive. UI updates are scheduled back onto the Tk mainloop via
`tk_root.after(0, ...)` when possible.
"""

import logging
from tkinter import messagebox
from typing import Callable

from docker_monitor.utils.process_worker import run_docker_cmd_in_process


class PruneManager:
    @staticmethod
    def prune_containers(status_bar, refresh_callback: Callable[[], None]):
        if not messagebox.askyesno('Confirm', 'Remove all stopped containers?'):
            return

        cmd = ['docker', 'container', 'prune', '--force']

        def _on_done(res):
            rc = res.get('returncode', 255)
            stderr = res.get('stderr_tail', '').strip()
            if rc == 0:
                try:
                    status_bar.after(0, lambda: status_bar.config(text='✅ Container prune completed'))
                    status_bar.after(0, refresh_callback)
                except Exception:
                    logging.exception('Failed to update UI after prune_containers')
            else:
                logging.error(f'Container prune failed, rc={rc}: {stderr}')
                try:
                    status_bar.after(0, lambda: status_bar.config(text=f'❌ Prune failed: {stderr[:200]}'))
                except Exception:
                    logging.exception('Failed to update UI on prune error')

        def _on_error(e):
            logging.exception('Error running container prune')

        logging.info('Scheduling container prune in process')
        run_docker_cmd_in_process(cmd, on_done=_on_done, on_error=_on_error, tk_root=status_bar, block=False)

    @staticmethod
    def prune_images(status_bar, refresh_callback: Callable[[], None]):
        if not messagebox.askyesno('Confirm', 'Remove all unused images?'):
            return

        cmd = ['docker', 'image', 'prune', '--all', '--force']

        def _on_done(res):
            rc = res.get('returncode', 255)
            stderr = res.get('stderr_tail', '').strip()
            if rc == 0:
                try:
                    status_bar.after(0, lambda: status_bar.config(text='✅ Image prune completed'))
                    status_bar.after(0, refresh_callback)
                except Exception:
                    logging.exception('Failed to update UI after prune_images')
            else:
                logging.error(f'Image prune failed, rc={rc}: {stderr}')
                try:
                    status_bar.after(0, lambda: status_bar.config(text=f'❌ Prune failed: {stderr[:200]}'))
                except Exception:
                    logging.exception('Failed to update UI on prune error')

        def _on_error(e):
            logging.exception('Error running image prune')

        logging.info('Scheduling image prune in process')
        run_docker_cmd_in_process(cmd, on_done=_on_done, on_error=_on_error, tk_root=status_bar, block=False)

    @staticmethod
    def prune_networks(status_bar, refresh_callback: Callable[[], None]):
        if not messagebox.askyesno('Confirm', 'Remove all unused networks?'):
            return

        cmd = ['docker', 'network', 'prune', '--force']

        def _on_done(res):
            rc = res.get('returncode', 255)
            stderr = res.get('stderr_tail', '').strip()
            if rc == 0:
                try:
                    status_bar.after(0, lambda: status_bar.config(text='✅ Network prune completed'))
                    status_bar.after(0, refresh_callback)
                except Exception:
                    logging.exception('Failed to update UI after prune_networks')
            else:
                logging.error(f'Network prune failed, rc={rc}: {stderr}')
                try:
                    status_bar.after(0, lambda: status_bar.config(text=f'❌ Prune failed: {stderr[:200]}'))
                except Exception:
                    logging.exception('Failed to update UI on prune error')

        def _on_error(e):
            logging.exception('Error running network prune')

        logging.info('Scheduling network prune in process')
        run_docker_cmd_in_process(cmd, on_done=_on_done, on_error=_on_error, tk_root=status_bar, block=False)

    @staticmethod
    def remove_all_stopped_containers(status_bar, refresh_callback: Callable[[], None]):
        if not messagebox.askyesno('Confirm', 'Remove ALL stopped containers?\nThis action cannot be undone.'):
            return

        cmd = ['bash', '-lc', "docker ps -a -f 'status=exited' -q | xargs -r docker rm -v"]

        def _on_done(res):
            rc = res.get('returncode', 255)
            stderr = res.get('stderr_tail', '').strip()
            if rc == 0:
                try:
                    status_bar.after(0, lambda: status_bar.config(text='✅ Removed stopped containers'))
                    status_bar.after(0, refresh_callback)
                except Exception:
                    logging.exception('Failed to update UI after remove_all_stopped_containers')
            else:
                logging.error(f'Remove stopped containers failed, rc={rc}: {stderr}')
                try:
                    status_bar.after(0, lambda: status_bar.config(text=f'❌ Remove failed: {stderr[:200]}'))
                except Exception:
                    logging.exception('Failed to update UI on remove error')

        def _on_error(e):
            logging.exception('Error removing stopped containers')

        logging.info('Scheduling remove_all_stopped_containers in process')
        run_docker_cmd_in_process(cmd, on_done=_on_done, on_error=_on_error, tk_root=status_bar, block=False)
"""Prune manager — small, safe wrappers that schedule pruning via worker."""

import logging
from tkinter import messagebox

from docker_monitor.utils.docker_utils import client, docker_lock


class PruneManager:
    @staticmethod
    def _run_in_worker(fn, *, block=True):
        # Import locally to avoid module-level worker dependency during import-time
        from docker_monitor.utils.worker import run_in_thread

        run_in_thread(fn, on_done=None, on_error=lambda e: logging.error(f"Prune failed: {e}"), tk_root=None, block=block)

    @staticmethod
    def prune_containers(status_bar, refresh_callback):
        if not messagebox.askyesno('Confirm', 'Remove all stopped containers?'):
            return

        """Prune manager — small, safe wrappers that schedule pruning via worker."""

        import logging
        from tkinter import messagebox

        from docker_monitor.utils.docker_utils import client, docker_lock


        class PruneManager:
            @staticmethod
            def _run_in_worker(fn, *, block=True):
                # Import locally to avoid module-level worker dependency during import-time
                from docker_monitor.utils.worker import run_in_thread

                run_in_thread(fn, on_done=None, on_error=lambda e: logging.error(f"Prune failed: {e}"), tk_root=None, block=block)

            @staticmethod
            def prune_containers(status_bar, refresh_callback):
                if not messagebox.askyesno('Confirm', 'Remove all stopped containers?'):
                    return

                def _task():
                    with docker_lock:
                        result = client.containers.prune()
                    count = len(result.get('ContainersDeleted', []))
                    try:
                        status_bar.after(0, lambda: status_bar.config(text=f"✅ Removed {count} containers"))
                        status_bar.after(0, refresh_callback)
                    except Exception:
                        logging.info("Prune completed but UI update failed")

                logging.info("Scheduling prune_containers")
                PruneManager._run_in_worker(_task, block=True)

            @staticmethod
            def prune_images(status_bar, refresh_callback):
                if not messagebox.askyesno('Confirm', 'Remove all unused images?'):
                    return

                def _task():
                    with docker_lock:
                        result = client.images.prune(filters={'dangling': False})
                    count = len(result.get('ImagesDeleted', []))
                    try:
                        status_bar.after(0, lambda: status_bar.config(text=f"✅ Removed {count} images"))
                        status_bar.after(0, refresh_callback)
                    except Exception:
                        logging.info("Image prune completed but UI update failed")

                logging.info("Scheduling prune_images")
                PruneManager._run_in_worker(_task, block=True)

            @staticmethod
            def prune_networks(status_bar, refresh_callback):
                if not messagebox.askyesno('Confirm', 'Remove all unused networks?'):
                    return

                def _task():
                    with docker_lock:
                        result = client.networks.prune()
                    count = len(result.get('NetworksDeleted', []))
                    try:
                        status_bar.after(0, lambda: status_bar.config(text=f"✅ Removed {count} networks"))
                        status_bar.after(0, refresh_callback)
                    except Exception:
                        logging.info("Network prune completed but UI update failed")

                logging.info("Scheduling prune_networks")
                PruneManager._run_in_worker(_task, block=True)

            @staticmethod
            def remove_all_stopped_containers(status_bar, refresh_callback):
                if not messagebox.askyesno('Confirm', 'Remove ALL stopped containers?\nThis action cannot be undone.'):
                    return

                def _task():
                    with docker_lock:
                        containers = client.containers.list(all=True, filters={'status': 'exited'})
                    removed = 0
                    for c in containers:
                        try:
                            c.remove()
                            removed += 1
                        except Exception:
                            logging.exception("Failed to remove container during bulk remove")
                    try:
                        status_bar.after(0, lambda: status_bar.config(text=f"✅ Removed {removed} containers"))
                        status_bar.after(0, refresh_callback)
                    except Exception:
                        logging.info("Bulk remove completed but UI update failed")

                logging.info("Scheduling remove_all_stopped_containers")
                PruneManager._run_in_worker(_task, block=False)
