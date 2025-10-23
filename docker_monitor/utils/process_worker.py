"""Process-backed worker utilities for running long blocking commands (docker CLI).

Provides a small wrapper around concurrent.futures.ProcessPoolExecutor to run
blocking CLI commands in separate processes and deliver results back to the
caller. Designed to keep long-running Docker operations off the Python GUI
threads and threads pool.

Usage:
  from docker_monitor.utils.process_worker import run_docker_cmd_in_process
  run_docker_cmd_in_process(['docker','pull','nginx:alpine'], on_done=..., on_error=..., tk_root=app)
"""
from __future__ import annotations

import concurrent.futures
import subprocess
import logging
from typing import Callable, List, Optional, Dict

# Tunable: number of parallel processes for heavy operations. Keep small to
# avoid overwhelming network / disk IO. Can be changed later or made
# configurable via environment variable.
DEFAULT_MAX_WORKERS = 2

# A single ProcessPoolExecutor for the application lifetime.
_executor: Optional[concurrent.futures.ProcessPoolExecutor] = None


def _get_executor() -> concurrent.futures.ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = concurrent.futures.ProcessPoolExecutor(max_workers=DEFAULT_MAX_WORKERS)
    return _executor


def _run_cmd(cmd: List[str]) -> Dict[str, object]:
    """Top-level worker function executed in a separate process.

    Returns a dict with keys: returncode, stdout_tail, stderr_tail
    """
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        # Keep only the last N characters to avoid huge IPC payloads
        tail_len = 16 * 1024
        return {
            'returncode': proc.returncode,
            'stdout_tail': stdout[-tail_len:],
            'stderr_tail': stderr[-tail_len:],
        }
    except Exception as e:
        return {
            'returncode': 255,
            'stdout_tail': '',
            'stderr_tail': f'Exception running command: {e}',
        }


def run_docker_cmd_in_process(cmd: List[str], *, on_done: Optional[Callable[[Dict[str, object]], None]] = None,
                              on_error: Optional[Callable[[Exception], None]] = None,
                              tk_root=None, block: bool = False) -> concurrent.futures.Future:
    """Submit a docker CLI command (or any command) to the process pool.

    - cmd: list of command parts, e.g. ['docker','pull','nginx:alpine']
    - on_done(result): called when the command completes with the result dict
    - on_error(exc): called if submitting/running the job fails
    - tk_root: optional tkinter root/widget; if provided, callbacks will be
      scheduled with `tk_root.after(0, ...)` so they run on the Tk main thread.
    - block: if True, wait for completion and return the Future's result.

    Returns the concurrent.futures.Future for the submitted job.
    """
    executor = _get_executor()
    try:
        fut = executor.submit(_run_cmd, cmd)
    except Exception as e:
        logging.exception("Failed to submit process job")
        if on_error:
            try:
                on_error(e)
            except Exception:
                logging.exception("on_error callback failed")
        raise

    def _cb(f: concurrent.futures.Future):
        try:
            res = f.result()
            if on_done:
                if tk_root is not None:
                    try:
                        tk_root.after(0, lambda: on_done(res))
                    except Exception:
                        # If scheduling fails, call directly (best-effort)
                        try:
                            on_done(res)
                        except Exception:
                            logging.exception("on_done handler failed")
                else:
                    try:
                        on_done(res)
                    except Exception:
                        logging.exception("on_done handler failed")
        except Exception as e:
            logging.exception("Process job raised exception in callback")
            if on_error:
                try:
                    if tk_root is not None:
                        try:
                            tk_root.after(0, lambda: on_error(e))
                        except Exception:
                            on_error(e)
                    else:
                        on_error(e)
                except Exception:
                    logging.exception("on_error handler failed")

    fut.add_done_callback(_cb)

    if block:
        # Wait for completion synchronously
        try:
            fut.result()
        except Exception:
            pass

    return fut
