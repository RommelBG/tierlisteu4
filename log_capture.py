# log_capture.py

import logging
import io

class InMemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_stream = io.StringIO()

    def emit(self, record):
        msg = self.format(record)
        self.log_stream.write(msg + "\n")

    def get_logs(self):
        return self.log_stream.getvalue()

    def clear_logs(self):
        self.log_stream.truncate(0)
        self.log_stream.seek(0)
