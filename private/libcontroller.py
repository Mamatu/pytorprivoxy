from stem.control import Controller

import logging
log = logging.getLogger("pytorprivoxy")

from pylibcommons import libprint

class _Controller:
    def __init__(self, port):
        self.controller = Controller.from_port(port = port)
    def add_event_listener(self, event_listener):
        extra_string = f"event_listener = {event_listener}"
        libprint.print_func_info(logger = log.debug, extra_string = extra_string)
        self.controller.add_event_listener(event_listener)
    def add_status_listener(self, status_listener):
        extra_string = f"status_listener = {status_listener}"
        libprint.print_func_info(logger = log.debug, extra_string = extra_string)
        self.controller.add_status_listener(status_listener)
    def authenticate(self, password):
        libprint.print_func_info(logger = log.debug)
        self.controller.authenticate(password = password)
    def signal(self, _signal):
        extra_string = f"signal = {_signal}"
        libprint.print_func_info(prefix = "+", logger = log.debug, extra_string = extra_string)
        output = None
        try:
            output = self.controller.signal(_signal)
        finally:
            extra_string = f"{extra_string} output = {output}" 
            libprint.print_func_info(prefix = "-", logger = log.debug, extra_string = extra_string)

def create(port):
    return _Controller(port)
