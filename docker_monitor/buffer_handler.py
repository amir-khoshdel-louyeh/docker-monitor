import logging
from collections import deque

# Global log buffer
log_buffer = deque(maxlen=1000)


class BufferHandler(logging.Handler):
    """Custom logging handler that stores log messages in a buffer."""
    
    def emit(self, record):
        log_entry = self.format(record)
        log_buffer.append(log_entry)
