import lib
__instances = []

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

def stop_all():
    global __instances
    for i in __instances: stop(i)

import atexit
atexit.register(stop_all)

import signal
def signal_handler(sig, frame):
    logging.info("Registering sig for application. It will stop all")
    stop_all()

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    import argparse
    import logging
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help = "start tor privoxy: socks_port, control_port, listen_port", type=int, nargs=3, action="append")
    parser.add_argument("--log_level", help = "logging debug: CRITICAL ERROR WARNING INFO DEBUG", type=str, default = "INFO")
    parser.add_argument("--timeout", help = "timeout for initialization, in the seconds. Default: 300s", type=int, default=300)
    parser.add_argument("--password_from_file", help = "Load password from file", type=str, default=None)
    factor_description = """
    Factor of success of initialization after what the app will be continued, otherwise it will interrupted.
    When is only one --start then it is ignored.
    """
    parser.add_argument("--success_factor", help = factor_description, type=float, default=1)
    args = parser.parse_args()
    if args.log_level:
        expected_levels = {"CRITICAL" : logging.CRITICAL, "ERROR" : logging.ERROR, "WARNING" : logging.WARNING, "INFO" : logging.INFO, "DEBUG" : logging.DEBUG}
        if not args.log_level in expected_levels.keys():
            raise Exception(f'{args.log_level} is not supported. Should be {",".join(expected_levels.keys())}')
        else:
            logging.basicConfig(level = expected_levels[args.log_level])
    args_dict = {"timeout" : args.timeout, "success_factor" : args.success_factor}
    if args.password_from_file:
        from private import libpass
        libpass.load_password_from_file(args.password_from_file)
    try:
        if args.start:
            if all(isinstance(p, list) for p in args.start):
                instances = start_multiple(args.start, **args_dict)
                for instance in instances:
                    instance.join()
            else:
                instance = start(*args.start, **args_dict)
                instance.join()
    except TimeoutError as te:
        logging.error(f"Timeout expired: {te}")
