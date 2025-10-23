import concurrent.futures
import threading
import logging
from functools import partial

# Shared ThreadPoolExecutor for I/O-bound tasks (Docker SDK calls)
# Tuned default: 16 workers for typical desktop; adjustable if needed.
_MAX_WORKERS = 16
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS)

# Bound the number of pending tasks to avoid unbounded memory growth during event storms.
# If the semaphore cannot be acquired, we drop low-priority tasks and call on_error if provided.
_MAX_PENDING = 128
_pending_semaphore = threading.BoundedSemaphore(_MAX_PENDING)


class TaskQueueFull(Exception):
    """Raised when the background task queue is full and a new task cannot be accepted."""


def _schedule_callback(tk_root, cb, arg=None):
    try:
        if tk_root:
            try:
                if arg is None:
                    tk_root.after(0, cb)
                else:
                    tk_root.after(0, lambda: cb(arg))
            except RuntimeError:
                # Tk mainloop not available (e.g., not started or already stopped).
                # Fall back to calling the callback synchronously. We catch
                # exceptions from the callback to avoid crashing the worker.
                logging.warning('Tk mainloop not available; invoking callback synchronously')
                try:
                    if arg is None:
                        cb()
                    else:
                        cb(arg)
                except Exception:
                    logging.exception('Error invoking callback synchronously after tk mainloop unavailable')
        else:
            if arg is None:
                cb()
            else:
                cb(arg)
    except Exception:
        logging.exception('Error scheduling callback')


def run_in_thread(fn, on_done=None, on_error=None, tk_root=None, block=False):
    """Run fn() in the shared thread pool with a bounded pending queue.

    - fn: callable with no args that returns a result
    - on_done: callable(result) to be executed on Tk main thread (if tk_root provided use after)
    - on_error: callable(exception) to be executed on Tk main thread
    - tk_root: the tk root window to use for scheduling UI callbacks via after(0)
    - block: if True, block until there's capacity in the pending queue; otherwise drop when full
    """

    acquired = False
    try:
        if block:
            _pending_semaphore.acquire()
            acquired = True
        else:
            acquired = _pending_semaphore.acquire(blocking=False)
    except Exception:
        acquired = False

    if not acquired:
        # Queue is saturated — inform caller via on_error if available and return
        logging.warning('Background task queue is full; dropping task')
        if on_error:
            _schedule_callback(tk_root, on_error, TaskQueueFull('task queue full'))
        return None

    def _task():
        try:
            result = fn()
            if on_done:
                _schedule_callback(tk_root, on_done, result)
        except Exception as e:
            logging.exception('Error in background task')
            if on_error:
                _schedule_callback(tk_root, on_error, e)
        finally:
            try:
                _pending_semaphore.release()
            except Exception:
                logging.exception('Error releasing pending semaphore')

    # Submit to executor
    try:
        fut = _executor.submit(_task)
        return fut
    except Exception as e:
        logging.exception('Failed to submit background task')
        try:
            _pending_semaphore.release()
        except Exception:
            pass
        if on_error:
            _schedule_callback(tk_root, on_error, e)
        return None
