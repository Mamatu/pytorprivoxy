import lib
__instances = []

def start(socks_port, control_port, listen_port, wait_for_initialization = True):
    global __instances
    callback_before_wait = lambda instance: __instances.append(instance)
    instance = lib.start(socks_port, control_port, listen_port, callback_before_wait = callback_before_wait, wait_for_initialization = wait_for_initialization)
    return instance

def start_multiple(ports : list, wait_for_initialization = True):
    global __instances
    print("start_multiple")
    callback_before_wait = lambda instance: __instances.append(instance)
    instances = lib.start_multiple(ports, callback_before_wait = callback_before_wait, wait_for_initialization = wait_for_initialization)
    return instances

def stop(instance):
    lib.stop(instance)
    global __instances
    __instances.remove(instance)

def stop_all():
    global __instances
    for instance in __instances:
        stop(instance)

import atexit
atexit.register(stop_all)

import signal
def signal_handler(sig, frame):
    stop_all()

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    import argparse
    import logging
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help = "start tor privoxy: socks_port, control_port, listen_port", type=int, nargs=3, action="append")
    parser.add_argument("--log_level", help = "logging debug: CRITICAL ERROR WARNING INFO DEBUG", type=str)
    args = parser.parse_args()
    if args.log_level:
        expected_levels = {"CRITICAL" : logging.CRITICAL, "ERROR" : logging.ERROR, "WARNING" : logging.WARNING, "INFO" : logging.INFO, "DEBUG" : logging.DEBUG}
        if not args.log_level in expected_levels.keys():
            raise Exception(f'{args.log_level} is not supported. Should be {",".join(expected_levels.keys())}')
        else:
            logging.basicConfig(level = expected_levels[args.log_level])
    if args.start:
        if all(isinstance(p, list) for p in args.start):
            instances = start_multiple(args.start)
            for instance in instances:
                instance.join()
        else:
            instance = start(*args.start)
            instance.join()
