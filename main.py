import lib
__instances = []

from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)

import logging
log = logging.getLogger("pytorprivoxy")

def _instances_append(instance):
    global __instances
    __instances.append(instance)

def _instances_remove(instance):
    global __instances
    if instance in __instances:
        __instances.remove(instance)

def start(socks_port, control_port, listen_port, wait_for_initialization = True, **kwargs):
    global __instances
    callback_before_wait = lambda instance: _instances_append(instance)
    return lib.start(socks_port, control_port, listen_port, callback_before_wait = callback_before_wait, wait_for_initialization = wait_for_initialization, **kwargs)

def start_multiple(ports : list, wait_for_initialization = True, **kwargs):
    global __instances
    callback_before_wait = lambda instance: _instances_append(instance)
    return lib.start_multiple(ports, callback_before_wait = callback_before_wait, wait_for_initialization = wait_for_initialization, **kwargs)

def stop(instance, remove_instance = True):
    lib.stop(instance)
    if remove_instance:
        _instances_remove(instance)

def stop_all():
    global __instances
    for i in __instances:
        stop(i, remove_instance = False)
    __instances = []

import atexit
atexit.register(stop_all)
server = None

import signal
def signal_handler(sig, frame):
    global server
    log.info("Registering sig for application. It will stop all")
    if server is not None: server.stop()
    stop_all()

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help = "start tor privoxy: socks_port, control_port, listen_port", type=int, nargs=3, action="append")
    parser.add_argument("--start_from_file", help = "like start but read ports from file", type=str)
    parser.add_argument("--log_level", help = "logging debug: CRITICAL ERROR WARNING INFO DEBUG", type=str, default = "INFO")
    parser.add_argument("--stdout", help = "logging into stdout", action='store_true')
    parser.add_argument("--timeout", help = "timeout for initialization, in the seconds. Default: 300s", type=int, default=300)
    parser.add_argument("--password_from_file", help = "Load password from file", type=str, default=None)
    parser.add_argument("--server", help = "Establish server to multiprocess communication. As argument it takes listen port", type=int, default=None)
    parser.add_argument("--find", help = "Path to directory when should be found epoal", type=str, default=None)
    factor_description = """
    Factor of success of initialization after what the app will be continued, otherwise it will interrupted.
    When is only one --start then it is ignored.
    """
    parser.add_argument("--success_factor", help = factor_description, type=float, default=1)
    args = parser.parse_args()
    if args.find:
        import os
        import sys
        for root, dirs, files in os.walk(args.find):
            for file in files:
                if file.endswith(".epoal"):
                    print(os.path.join(root, file))
        sys.exit(0)
    if args.log_level:
        lib.set_logging_level(args.log_level)
    if args.stdout:
        lib.enable_stdout()
    args_dict = {"timeout" : args.timeout, "success_factor" : args.success_factor}
    if args.password_from_file:
        from private import libpass
        libpass.load_password_from_file(args.password_from_file)
    try:
        def start_from_args(ports, server, **args_dict):
            if all(isinstance(p, list) for p in ports):
                instances = start_multiple(ports, **args_dict, server = server)
                server = None
                if isinstance(instances, tuple):
                    server = instances[1]
                    instances = instances[0]
                for instance in instances:
                    instance.join()
            else:
                instance = start(*ports, server = server, **args_dict)
                if isinstance(instances, tuple):
                    server = instances[1]
                    instances = instances[0]
                instance.join()
        server = None
        if args.start:
            start_from_args(args.start, args.server, **args_dict)
        elif args.start_from_file:
            ports_all = []
            with open(args.start_from_file, "r") as f:
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
            start_from_args(ports_all, args.server, **args_dict)
    except TimeoutError as te:
        log.error(f"Timeout expired: {te}")
