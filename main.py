import lib
__instances = []

from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)

import logging
log = logging.getLogger("pytorprivoxy")

from pylibcommons import libkw, libthread

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

def get_count_of_instances():
    global __instances
    return len(__instances)

def get_instance(index):
    global __instances
    return __instances[index]

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

def main():
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
    start_main(**vars(args))

def start_main(**kwargs):
    arg_log_level = libkw.handle_kwargs("log_level", default_output = "INFO", **kwargs)
    arg_stdout = libkw.handle_kwargs("stdout", default_output = False, **kwargs)
    arg_password_from_file = libkw.handle_kwargs("password_from_file", default_output = None, **kwargs)
    arg_start = libkw.handle_kwargs("start", default_output = None, **kwargs)
    arg_start_from_file = libkw.handle_kwargs("start_from_file", default_output = None, **kwargs)
    arg_server = libkw.handle_kwargs("server", default_output = None, **kwargs)
    arg_timeout = libkw.handle_kwargs("timeout", default_output = 300, **kwargs)
    arg_success_factor = libkw.handle_kwargs("success_factor", default_output = 1., **kwargs)
    if arg_log_level:
        lib.set_logging_level(arg_log_level)
    if arg_stdout:
        lib.enable_stdout()
    args_dict = {"timeout" : arg_timeout, "success_factor" : arg_success_factor}
    if arg_password_from_file:
        from private import libpass
        libpass.load_password_from_file(arg_password_from_file)
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
                instance = start(*ports, server = arg_server, **args_dict)
                if isinstance(instance, tuple):
                    server = instance[1]
                    instance = instance[0]
                instance.join()
        server = None
        if arg_start:
            start_from_args(arg_start, server, **args_dict)
        elif arg_start_from_file:
            ports_all = []
            with open(arg_start_from_file, "r") as f:
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
            start_from_args(ports_all, arg_server, **args_dict)
    except TimeoutError as te:
        log.error(f"Timeout expired: {te}")
    except Exception as e:
        log.error(f"Exception: {e}")
        raise e

def start_main_async(**kwargs):
    arg_log_level = libkw.handle_kwargs("log_level", default_output = "INFO", **kwargs)
    if arg_log_level:
        lib.set_logging_level(arg_log_level)
    def target(stop_control, **kwargs):
        start_main(**kwargs)
    thread = libthread.Thread(target = target, kwargs = kwargs)
    thread.start()
    return thread, thread.get_stop_control()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import sys
        sys.exit(1)
