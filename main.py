import lib
__instances = []

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
    callback_before_wait = lambda instance: __instances_append(instance)
    instance = lib.start(socks_port, control_port, listen_port, callback_before_wait = callback_before_wait, wait_for_initialization = wait_for_initialization, **kwargs)
    return instance

def start_multiple(ports : list, wait_for_initialization = True, **kwargs):
    global __instances
    callback_before_wait = lambda instance: _instances_append(instance)
    instances = lib.start_multiple(ports, callback_before_wait = callback_before_wait, wait_for_initialization = wait_for_initialization, **kwargs)
    return instances

def stop(instance):
    lib.stop(instance)
    _instances_remove(instance)

_named_fifo_path = None

def stop_named_fifo():
    global _named_fifo_path
    if _named_fifo_path:
        import os, stat
        if os.path.exists(_named_fifo_path) and stat.S_ISFIFO(os.stat(_named_fifo_path).st_mode):
            os.system(f"echo \"stop\" > {_named_fifo_path}")
            os.remove(_named_fifo_path)

def stop_all():
    global __instances
    stop_named_fifo()
    for i in __instances: stop(i)

import atexit
atexit.register(stop_all)

import signal
def signal_handler(sig, frame):
    log.info("Registering sig for application. It will stop all")
    stop_all()

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    import os
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help = "start tor privoxy: socks_port, control_port, listen_port", type=int, nargs=3, action="append")
    parser.add_argument("--log_level", help = "logging debug: CRITICAL ERROR WARNING INFO DEBUG", type=str, default = "INFO")
    parser.add_argument("--stdout", help = "logging into stdout", action='store_true')
    parser.add_argument("--timeout", help = "timeout for initialization, in the seconds. Default: 300s", type=int, default=300)
    parser.add_argument("--password_from_file", help = "Load password from file", type=str, default=None)
    parser.add_argument("--mkfifo", help = "Make named pipe to comunicate with privoxy", type=str, default="/tmp/privoxy.fifo")
    factor_description = """
    Factor of success of initialization after what the app will be continued, otherwise it will interrupted.
    When is only one --start then it is ignored.
    """
    parser.add_argument("--success_factor", help = factor_description, type=float, default=1)
    args = parser.parse_args()
    if args.log_level:
        lib.set_logging_level(args.log_level)
    if args.stdout:
        lib.enable_stdout()
    args_dict = {"timeout" : args.timeout, "success_factor" : args.success_factor}
    if args.password_from_file:
        from private import libpass
        libpass.load_password_from_file(args.password_from_file)
    try:
        if args.start:
            mkfifo = None
            if args.mkfifo:
                mkfifo = args.mkfifo
                _named_fifo_path = mkfifo
            if all(isinstance(p, list) for p in args.start):
                instances = start_multiple(args.start, **args_dict, mkfifo = mkfifo)
                for instance in instances:
                    instance.join()
            else:
                instance = start(*args.start, **args_dict)
                instance.join()
    except TimeoutError as te:
        log.error(f"Timeout expired: {te}")
