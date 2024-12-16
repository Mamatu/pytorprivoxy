import lib

from signal import signal, SIGPIPE, SIGINT, SIG_DFL
signal(SIGPIPE, SIG_DFL)

import logging
log = logging.getLogger('pytorprivoxy')

from pylibcommons import libkw, libthread, libprint, libprocess

class PyTorPrivoxyContext:
    class Ctx:
        def __init__(self, output, root_ctx):
            self.instances = output.get("instances", None)
            self.server = output.get("server", None)
            self.futures = output.get("futures", None)
            self.root_ctx = root_ctx
        def stop_all(self):
            lib.stop(self.instances)
            self.root_ctx.stop_server()
        def get_pids(self):
            return lib.get_pids(self.instances)
    def __init__(self, ports, **kwargs):
        self.ports = ports
        self.kwargs = kwargs
        self.instances = None
        self.server = None
    def __enter__(self):
        libprint.print_func_info(logger = log.debug)
        try:
            output = None
            if all(isinstance(p, list) for p in self.ports):
                output = lib.start_multiple(self.ports, **self.kwargs)
            else:
                output = lib.start(*self.ports, **self.kwargs)
            self.instances = output.get("instances", None)
            self.server = output.get("server", None)
            return PyTorPrivoxyContext.Ctx(output, self)
        finally:
            libprint.print_func_info(logger = log.debug)
    def __exit__(self, exc_type, exc_val, exc_tb):
        libprint.print_func_info(logger = log.debug)
        if exc_type:
            libprint.print_func_info(logger = log.debug)
            lib.stop(self.instances)
            try:
                lib.join(self.instances)
            finally:
                self.stop_server()
            log_string = f"{exc_type} {exc_val} {exc_tb}"
            libprint.print_func_info(logger = log.error, extra_string = log_string)
            libprint.print_func_info(logger = log.debug)
            raise exc_val
        lib.stop(self.instances)
        try:
            lib.join(self.instances)
        finally:
            libprint.print_func_info(logger = log.debug)
            self.stop_server()
        libprint.print_func_info(logger = log.debug)
    def stop_server(self):
        libprint.print_func_info(logger = log.debug)
        if self.server:
            self.server.stop()

class PyTorPrivoxyAppContext:
    def __init__(self, **kwargs):
        self.log_level = libkw.handle_kwargs("log_level", default_output = "DEBUG", **kwargs)
        self.stdout = libkw.handle_kwargs("stdout", default_output = False, **kwargs)
        self.password_from_file = libkw.handle_kwargs("password_from_file", default_output = None, **kwargs)
        self.start = libkw.handle_kwargs("start", default_output = None, **kwargs)
        self.start_from_file = libkw.handle_kwargs("start_from_file", default_output = None, **kwargs)
        self.server_port = libkw.handle_kwargs("server_port", default_output = None, **kwargs)
        self.timeout = libkw.handle_kwargs("timeout", default_output = 300, **kwargs)
        self.success_factor = libkw.handle_kwargs("success_factor", default_output = 1., **kwargs)
        self.wait_for_initialization = libkw.handle_kwargs("wait_for_initialization", default_output = False, **kwargs)
        self.tor_privoxy_ctx = None
    def __enter__(self):
        libprint.print_func_info(logger = log.info)
        if self.log_level:
            lib.set_logging_level(self.log_level)
        if self.stdout:
            lib.enable_stdout()
        args_dict = {}
        args_dict["timeout"] = self.timeout
        args_dict["success_factor"] = self.success_factor
        args_dict["wait_for_initialization"] = self.wait_for_initialization
        if self.password_from_file:
            from private import libpass
            libpass.load_password_from_file(self.password_from_file)
        _ports = None
        if self.start:
            _ports = self.start
        elif self.start_from_file:
            ports_all = []
            with open(self.start_from_file, "r") as f:
                lines = f.readlines()
            for line in lines:
                ports = line.split()
                if len(ports) != 3:
                    raise Exception(f"Line {line} contains invalid number of prots (it must be 3)")
                try:
                    ports = [int(p) for p in ports]
                except ValueError:
                    raise Exception(f"Element of {ports} cannot be converted into int")
                ports_all.append(list(ports))
            _ports = ports_all
        self.tor_privoxy_ctx = PyTorPrivoxyContext(_ports, server_port = self.server_port, **args_dict)
        libprint.print_func_info(logger = log.info)
        return self.tor_privoxy_ctx.__enter__()
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tor_privoxy_ctx.__exit__(exc_type, exc_val, exc_tb)

def main(callback = lambda ctx: None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help = "start tor privoxy: socks_port, control_port, listen_port", type=int, nargs=3, action="append")
    parser.add_argument("--start_from_file", help = "like start but read ports from file", type=str)
    parser.add_argument("--log_level", help = "logging debug: CRITICAL ERROR WARNING INFO DEBUG", type=str, default = "INFO")
    parser.add_argument("--stdout", help = "logging into stdout", action='store_true')
    parser.add_argument("--timeout", help = "timeout for initialization, in the seconds. Default: 300s", type=int, default=300)
    parser.add_argument("--password_from_file", help = "Load password from file", type=str, default=None)
    parser.add_argument("--server", help = "Establish server to multiprocess communication. As argument it takes listen port", type=int, default=None)
    factor_description = """
    Factor of success of initialization after what the app will be continued, otherwise it will interrupted.
    When is only one --start then it is ignored.
    """
    parser.add_argument("--success_factor", help = factor_description, type=float, default=1)
    args = parser.parse_args()
    with PyTorPrivoxyAppContext(**vars(args)) as ctx:
        callback(ctx)

def start_main_async(callback = None, **kwargs):
    arg_log_level = libkw.handle_kwargs("log_level", default_output = "DEBUG", **kwargs)
    if arg_log_level:
        lib.set_logging_level(arg_log_level)
    def target(stop_control, **_kwargs):
        libprint.print_func_info(logger = log.info, extra_string = f"kwargs {_kwargs}")
        with PyTorPrivoxyAppContext(**_kwargs) as ctx:
            callback(ctx, stop_control)
    thread = libthread.Thread(target = target, kwargs = kwargs)
    thread.start()
    return thread

import sys
import threading

event = threading.Event()

def sigint_handler(signal, frame):
    event.set()

def sigint_callback(ctx):
    event.wait()
    ctx.stop_all()

if __name__ == "__main__":
    try:
        signal(SIGINT, sigint_handler)
        main(callback = sigint_callback)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        libprint.print_func_info(extra_string = f"{e} {tb}", logger = log.error)
        import sys
        sys.exit(1)
