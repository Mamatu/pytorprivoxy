import lib
__instances = []

def start(socks_port, control_port, listen_port, wait_for_initialization = True):
    global __instances
    instance = lib.start(socks_port, control_port, listen_port, wait_for_initialization = False)
    __instances.append(instance)
    if wait_for_initialization:
        instance.wait_for_initialization()
    return instance

def start_multiple(ports : list):
    global __instances
    instances = lib.start(socks_port, control_port, listen_port, wait_for_initialization)
    for instance in instances:
        __instances.append(instance)
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
    parser.add_argument("--start", help = "start tor privoxy: socks_port, control_port, listen_port", type=int, nargs=3)
    parser.add_argument("--log_level", help = "logging debug: CRITICAL ERROR WARNING INFO DEBUG", type=str)
    args = parser.parse_args()
    if args.log_level:
        expected_levels = {"CRITICAL" : logging.CRITICAL, "ERROR" : logging.ERROR, "WARNING" : logging.WARNING, "INFO" : logging.INFO, "DEBUG" : logging.DEBUG}
        if not args.log_level in expected_levels.keys():
            raise Exception(f'{args.log_level} is not supported. Should be {",".join(expected_levels.keys())}')
        else:
            logging.basicConfig(level = expected_levels[args.log_level])
    if args.start:
        ports = tuple(args.start)
        instance = start(ports[0], ports[1], ports[2])
        instance.wait_for_processes_kill()
