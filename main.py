import lib
__instances = []

def start(socks_port, control_port, listen_port, wait_for_initialization = True):
    global __instances
    instance = lib.start(socks_port, control_port, listen_port, wait_for_initialization = False)
    __instances.append(instance)
    print(f"start: {__instances}")
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

def stop_all():
    global __instances
    print(f"stop_all: {__instances}")
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help = "start tor privoxy: socks_port, control_port, listen_port", type=int, nargs=3)
    parser.add_argument("--logging", help = "start logging", action="store_true")
    args = parser.parse_args()
    if args.start:
        ports = tuple(args.start)
        instance = start(ports[0], ports[1], ports[2])
        instance.wait_for_processes_kill()
