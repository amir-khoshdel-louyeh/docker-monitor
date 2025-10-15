"""
Docker Monitor Manager
Main entry point for the application.
"""

import logging
from docker_monitor.utils.buffer_handler import BufferHandler
from docker_monitor.gui.docker_monitor_app import DockerMonitorApp, main

# Setup logging with buffer handler
buffer_handler = BufferHandler()
buffer_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logging.getLogger().addHandler(buffer_handler)
logging.getLogger().setLevel(logging.INFO)

# Entry point
if __name__ == "__main__":
    main()
